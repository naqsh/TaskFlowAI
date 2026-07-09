"""Local LLM provider via Ollama API (TF-053)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from backend.llm.router import LLMProviderProtocol, LLMResponse
from backend.logging_config import get_logger
from backend.metrics import LOCAL_LLM_LATENCY_SECONDS, LOCAL_LLM_REQUESTS_TOTAL

logger = get_logger(__name__)


class LLMError(Exception):
    """Raised when local LLM invocation fails."""


class LocalLLMProvider(LLMProviderProtocol):
    """Ollama-backed local LLM for privacy-sensitive requests."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        max_context_tokens: int = 4096,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_context_tokens = max_context_tokens
        self._client = http_client

    def _truncate_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Truncate context when exceeding local model window."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        approx_tokens = total_chars // 4
        if approx_tokens <= self._max_context_tokens:
            return messages
        logger.warning(
            "local_llm_context_truncated",
            approx_tokens=approx_tokens,
            max_tokens=self._max_context_tokens,
        )
        # Keep system + last user message only.
        if len(messages) <= 2:
            return messages
        truncated = [messages[0], messages[-1]]
        return truncated

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        reasoning_effort: str,
    ) -> LLMResponse:
        _ = reasoning_effort
        resolved_model = model if model else self._model
        truncated = self._truncate_messages(messages)
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in truncated)

        start = time.perf_counter()
        client = self._client or httpx.AsyncClient(timeout=60.0)
        owns_client = self._client is None
        try:
            resp = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": resolved_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            if resp.status_code != 200:
                raise LLMError(
                    f"ollama_unavailable status={resp.status_code} "
                    f"hint=ensure Ollama is running at {self._base_url}"
                )
            data: dict[str, Any] = resp.json()
            content = str(data.get("response", ""))
            eval_count = int(data.get("eval_count", 0))
            prompt_eval_count = int(data.get("prompt_eval_count", 0))
        except httpx.HTTPError as exc:
            raise LLMError(f"ollama_unreachable base_url={self._base_url} error={exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        duration = time.perf_counter() - start
        LOCAL_LLM_REQUESTS_TOTAL.inc()
        LOCAL_LLM_LATENCY_SECONDS.observe(duration)

        return LLMResponse(
            content=content,
            model_used=f"local:{resolved_model}",
            tokens_input=prompt_eval_count,
            tokens_output=eval_count,
            cache_read_tokens=0,
            latency_ms=int(duration * 1000),
        )
