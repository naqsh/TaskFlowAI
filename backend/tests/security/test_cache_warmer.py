"""Tests for prompt cache warmer (TF-058)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from backend.llm.cache_warmer import PromptCacheWarmer
from backend.llm.deterministic import DeterministicPlannerProvider
from backend.llm.router import LLMRouter


class _CachingProvider(DeterministicPlannerProvider):
    def __init__(self) -> None:
        self.call_count = 0

    async def generate(self, *, messages, model, max_tokens, reasoning_effort):  # type: ignore[no-untyped-def]
        self.call_count += 1
        resp = await super().generate(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
        cache_read = 1 if self.call_count > 1 else 0
        return resp.__class__(
            content=resp.content,
            model_used=resp.model_used,
            tokens_input=resp.tokens_input,
            tokens_output=resp.tokens_output,
            cache_read_tokens=cache_read,
            latency_ms=resp.latency_ms,
        )


@pytest.mark.asyncio
async def test_warmer_populates_cache_on_second_call() -> None:
    provider = _CachingProvider()
    warmer = PromptCacheWarmer(
        router=LLMRouter(primary_provider=provider),
        enabled=True,
        cache_ttl_seconds=300,
    )
    await warmer.warm_cache("planner")
    await warmer.warm_cache("planner")
    assert provider.call_count == 2
    assert warmer._last_warmed.get("planner") is not None


@pytest.mark.asyncio
async def test_disabled_warmer_skips_background_task() -> None:
    warmer = PromptCacheWarmer(
        router=LLMRouter(primary_provider=DeterministicPlannerProvider()),
        enabled=False,
    )
    warmer.start()
    assert warmer._task is None


def test_peak_vs_off_peak_interval() -> None:
    warmer = PromptCacheWarmer(
        router=LLMRouter(primary_provider=DeterministicPlannerProvider()),
        enabled=True,
    )
    peak = warmer._warm_interval(datetime(2026, 7, 9, 10, 0, tzinfo=UTC))
    off_peak = warmer._warm_interval(datetime(2026, 7, 9, 22, 0, tzinfo=UTC))
    assert peak < off_peak


@pytest.mark.asyncio
async def test_keep_warm_cancellable() -> None:
    warmer = PromptCacheWarmer(
        router=LLMRouter(primary_provider=DeterministicPlannerProvider()),
        enabled=True,
    )
    warmer.start()
    await asyncio.sleep(0.05)
    await warmer.stop()
    assert warmer._task is None
