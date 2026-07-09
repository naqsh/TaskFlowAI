from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Protocol

from backend.metrics import (
    CACHED_TOKENS_SAVED_TOTAL,
    PROMPT_CACHE_HIT_RATE,
    PROMPT_CACHE_HITS_TOTAL,
    PROMPT_CACHE_MISSES_TOTAL,
)


class RateLimitedError(Exception):
    """Raised when an upstream LLM provider rate limits the request."""

    def __init__(self, status_code: int = 429) -> None:
        self.status_code = status_code
        super().__init__(f"rate_limited status_code={status_code}")


class TokenBudgetExceededError(Exception):
    """Raised when the combined token usage exceeds the circuit-break limit."""


class LLMProviderProtocol(Protocol):
    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        reasoning_effort: str,
    ) -> LLMResponse: ...


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model_used: str
    tokens_input: int
    tokens_output: int
    cache_read_tokens: int
    latency_ms: int


class LLMRouter:
    """Provider router with primary → fallback → local behavior (TF-053)."""

    def __init__(
        self,
        *,
        primary_provider: LLMProviderProtocol,
        fallback_provider: LLMProviderProtocol | None = None,
        local_provider: LLMProviderProtocol | None = None,
        token_budget_tokens: int = 8000,
    ) -> None:
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._local = local_provider
        self._token_budget_tokens = token_budget_tokens

    _PROMPT_CACHE_HITS = 0
    _PROMPT_CACHE_MISSES = 0

    @staticmethod
    def build_cached_system_messages(
        *,
        stable_blocks: list[str],
        dynamic_content: str,
        prompt_version: str = "v2.0.0",
        provider: Literal["claude", "openai", "other"] = "claude",
    ) -> list[dict[str, object]]:
        """Structure system prompts for provider prefix/ephemeral caching (TF-039).

        Claude: attaches ``cache_control: {type: ephemeral}`` on the last stable block.
        OpenAI: concatenates a stable prefix (>=1024 tokens preferred) before dynamic content.
        Dynamic user content is always appended last so it is never cached.
        """

        versioned = [*stable_blocks, f"prompt_version={prompt_version}"]
        messages: list[dict[str, object]] = []
        if provider == "claude":
            for i, block in enumerate(versioned):
                msg: dict[str, object] = {"role": "system", "content": block}
                if i == len(versioned) - 1:
                    msg["cache_control"] = {"type": "ephemeral"}
                messages.append(msg)
        else:
            # OpenAI / other: single stable system prefix (whitespace-sensitive for caching).
            messages.append({"role": "system", "content": "\n\n".join(versioned)})
        messages.append({"role": "user", "content": dynamic_content})
        return messages

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        reasoning_effort: Literal["high", "xhigh"] | str = "high",
        effort: Literal["xhigh", "high", "medium", "low"] | str | None = None,
        force_local: bool = False,
    ) -> LLMResponse:
        _ = effort  # Forward-compatibility; router forwards reasoning_effort only.

        if not messages:
            raise ValueError("messages must not be empty")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")

        start = time.perf_counter()
        provider = self._select_provider(force_local=force_local)
        try:
            resp = await provider.generate(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                reasoning_effort=str(reasoning_effort),
            )
        except RateLimitedError:
            if self._fallback is None:
                raise
            resp = await self._fallback.generate(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                reasoning_effort=str(reasoning_effort),
            )

        duration_ms = int((time.perf_counter() - start) * 1000)
        tokens_total = resp.tokens_input + resp.tokens_output
        if tokens_total > 2 * self._token_budget_tokens:
            raise TokenBudgetExceededError(f"token_budget exceeded tokens_total={tokens_total}")

        # Prompt cache metrics (TF-039). Providers must populate `cache_read_tokens`.
        cache_hit = resp.cache_read_tokens > 0
        if cache_hit:
            LLMRouter._PROMPT_CACHE_HITS += 1
            PROMPT_CACHE_HITS_TOTAL.inc()
            CACHED_TOKENS_SAVED_TOTAL.inc(resp.cache_read_tokens)
        else:
            LLMRouter._PROMPT_CACHE_MISSES += 1
            PROMPT_CACHE_MISSES_TOTAL.inc()

        total = LLMRouter._PROMPT_CACHE_HITS + LLMRouter._PROMPT_CACHE_MISSES
        PROMPT_CACHE_HIT_RATE.set(
            LLMRouter._PROMPT_CACHE_HITS / total if total > 0 else 0.0,
        )

        # Ensure latency_ms is always set (providers may omit it in tests).
        if resp.latency_ms <= 0:
            resp = LLMResponse(
                content=resp.content,
                model_used=resp.model_used,
                tokens_input=resp.tokens_input,
                tokens_output=resp.tokens_output,
                cache_read_tokens=resp.cache_read_tokens,
                latency_ms=duration_ms,
            )
        return resp

    def _select_provider(self, *, force_local: bool) -> LLMProviderProtocol:
        if force_local:
            if self._local is None:
                from backend.llm.local import LLMError

                raise LLMError("local_llm_disabled force_local=true but no local provider")
            return self._local
        return self._primary
