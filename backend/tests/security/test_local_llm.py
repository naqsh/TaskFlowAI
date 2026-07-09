"""Local LLM provider tests (TF-053)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from backend.llm.deterministic import DeterministicPlannerProvider
from backend.llm.local import LLMError, LocalLLMProvider
from backend.llm.router import LLMRouter


@pytest.mark.asyncio
async def test_force_local_calls_local_provider() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": '{"mode":"create_task","task_draft":{"title":"t","priority":"low"}}',
        "eval_count": 5,
        "prompt_eval_count": 10,
    }
    client = AsyncMock()
    client.post = AsyncMock(return_value=mock_response)
    client.aclose = AsyncMock()

    local = LocalLLMProvider(http_client=client)
    router = LLMRouter(
        primary_provider=DeterministicPlannerProvider(),
        local_provider=local,
    )
    resp = await router.generate(
        messages=[{"role": "user", "content": "confidential_pii task"}],
        model="llama3.1",
        max_tokens=100,
        reasoning_effort="high",
        force_local=True,
    )
    assert resp.model_used.startswith("local:")
    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_local_without_provider_raises() -> None:
    router = LLMRouter(
        primary_provider=DeterministicPlannerProvider(),
        local_provider=None,
    )
    with pytest.raises(LLMError, match="local_llm_disabled"):
        await router.generate(
            messages=[{"role": "user", "content": "x"}],
            model="llama3.1",
            max_tokens=10,
            reasoning_effort="high",
            force_local=True,
        )


@pytest.mark.asyncio
async def test_ollama_unavailable_raises_clear_error() -> None:
    client = AsyncMock()
    client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    client.aclose = AsyncMock()
    local = LocalLLMProvider(http_client=client)
    with pytest.raises(LLMError, match="ollama_unreachable"):
        await local.generate(
            messages=[{"role": "user", "content": "test"}],
            model="llama3.1",
            max_tokens=10,
            reasoning_effort="high",
        )
