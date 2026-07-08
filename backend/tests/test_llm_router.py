from __future__ import annotations

import pytest

from backend.llm.router import LLMResponse, LLMRouter, RateLimitedError, TokenBudgetExceededError


class Provider:
    def __init__(
        self,
        *,
        response: LLMResponse | None = None,
        raise_rate_limited: bool = False,
        calls: list[int] | None = None,
    ) -> None:
        self._response = response
        self._raise_rate_limited = raise_rate_limited
        self._calls = calls

    async def generate(
        self, *, messages: list[dict[str, str]], model: str, max_tokens: int, reasoning_effort: str
    ) -> LLMResponse:
        if self._calls is not None:
            self._calls[0] += 1
        if self._raise_rate_limited:
            raise RateLimitedError(status_code=429)
        assert self._response is not None
        return self._response


@pytest.mark.asyncio
async def test_llm_router_falls_back_on_rate_limit() -> None:
    primary_calls = [0]
    fallback_calls = [0]
    primary = Provider(
        raise_rate_limited=True,
        calls=primary_calls,
    )
    fallback = Provider(
        response=LLMResponse(
            content="ok",
            model_used="gpt-4o-mini",
            tokens_input=1,
            tokens_output=1,
            cache_read_tokens=0,
            latency_ms=0,
        ),
        calls=fallback_calls,
    )
    router = LLMRouter(primary_provider=primary, fallback_provider=fallback)

    resp = await router.generate(
        messages=[{"role": "user", "content": "x"}],
        model="gpt-5.5",
        max_tokens=10,
        reasoning_effort="high",
    )
    assert resp.content == "ok"
    assert primary_calls[0] == 1
    assert fallback_calls[0] == 1


@pytest.mark.asyncio
async def test_llm_router_token_budget_exceeded() -> None:
    router = LLMRouter(
        primary_provider=Provider(
            response=LLMResponse(
                content="big",
                model_used="gpt-5.5",
                tokens_input=100,
                tokens_output=100,
                cache_read_tokens=0,
                latency_ms=0,
            ),
        ),
        fallback_provider=None,
        token_budget_tokens=50,
    )

    with pytest.raises(TokenBudgetExceededError):
        await router.generate(
            messages=[{"role": "user", "content": "x"}],
            model="gpt-5.5",
            max_tokens=10,
            reasoning_effort="high",
        )


@pytest.mark.asyncio
async def test_llm_router_rejects_empty_messages() -> None:
    router = LLMRouter(
        primary_provider=Provider(
            response=LLMResponse(
                content="ok",
                model_used="gpt-5.5",
                tokens_input=1,
                tokens_output=1,
                cache_read_tokens=0,
                latency_ms=0,
            ),
        ),
    )
    with pytest.raises(ValueError):
        await router.generate(messages=[], model="gpt-5.5", max_tokens=10, reasoning_effort="high")
