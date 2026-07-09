"""Prompt cache warming background service (TF-058)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.llm.prompt_loader import AgentName, load_agent_prompt_pack
from backend.llm.router import LLMRouter
from backend.logging_config import get_logger

if TYPE_CHECKING:
    from backend.llm.router import LLMProviderProtocol

logger = get_logger(__name__)

_AGENT_IDS: tuple[AgentName, ...] = (
    "context",
    "planner",
    "verification",
    "adversarial",
    "critic",
    "orchestrator",
)

PEAK_WARM_INTERVAL_SECONDS = 240  # 4 minutes
OFF_PEAK_WARM_INTERVAL_SECONDS = 900  # 15 minutes
STAGGER_SECONDS = 10
LOW_TRAFFIC_REQ_PER_MIN = 1.0


@dataclass
class PromptCacheWarmer:
    """Background task that pings LLM providers with stable system prompts to keep cache warm."""

    router: LLMRouter
    enabled: bool = True
    cache_ttl_seconds: int = 300
    peak_start_hour: int = 8
    peak_end_hour: int = 18
    _last_warmed: dict[str, datetime] = field(default_factory=dict)
    _request_counts: dict[str, int] = field(default_factory=dict)
    _task: asyncio.Task[None] | None = field(default=None, repr=False)

    def record_request(self, agent_id: str) -> None:
        """Track per-agent traffic for low-traffic skip logic."""

        self._request_counts[agent_id] = self._request_counts.get(agent_id, 0) + 1

    def _is_peak_hours(self, now: datetime) -> bool:
        return self.peak_start_hour <= now.hour < self.peak_end_hour

    def _warm_interval(self, now: datetime) -> int:
        return (
            PEAK_WARM_INTERVAL_SECONDS
            if self._is_peak_hours(now)
            else OFF_PEAK_WARM_INTERVAL_SECONDS
        )

    async def warm_cache(self, agent_id: AgentName) -> None:
        """Send a minimal-token ping with the agent's cached system prompt blocks."""

        try:
            pack = load_agent_prompt_pack(agent_id)
            stable_blocks = [b["content"] for b in pack.assemble_system_blocks()]
            messages = LLMRouter.build_cached_system_messages(
                stable_blocks=stable_blocks,
                dynamic_content="cache_warm_ping",
                prompt_version=pack.version,
                provider="claude",
            )
            await self.router.generate(
                messages=messages,  # type: ignore[arg-type]
                model="gpt-4o-mini",
                max_tokens=1,
                reasoning_effort="low",
            )
            self._last_warmed[agent_id] = datetime.now(UTC)
            logger.debug("cache_warmed", agent_id=agent_id)
        except Exception as exc:
            logger.warning("cache_warm_failed", agent_id=agent_id, error=str(exc))

    async def keep_warm(self) -> None:
        """Run until cancelled — staggered warming per agent."""

        if not self.enabled:
            logger.info("cache_warming_disabled")
            return

        while True:
            now = datetime.now(UTC)
            interval = self._warm_interval(now)
            for index, agent_id in enumerate(_AGENT_IDS):
                if self._request_counts.get(agent_id, 0) < LOW_TRAFFIC_REQ_PER_MIN:
                    last = self._last_warmed.get(agent_id)
                    if last and (now - last).total_seconds() < interval:
                        continue
                if index > 0:
                    await asyncio.sleep(STAGGER_SECONDS)
                await self.warm_cache(agent_id)
            await asyncio.sleep(interval)

    def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        self._task = asyncio.create_task(self.keep_warm(), name="prompt-cache-warmer")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None


def build_cache_warmer(
    *,
    provider: LLMProviderProtocol,
    enabled: bool,
    cache_ttl_seconds: int,
) -> PromptCacheWarmer:
    router = LLMRouter(primary_provider=provider)
    return PromptCacheWarmer(
        router=router,
        enabled=enabled,
        cache_ttl_seconds=cache_ttl_seconds,
    )
