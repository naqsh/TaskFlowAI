"""Deterministic LLM provider for local development and tests."""

from __future__ import annotations

import json
from datetime import date, timedelta

from backend.llm.router import LLMProviderProtocol, LLMResponse


class DeterministicPlannerProvider(LLMProviderProtocol):
    """Local fallback provider so `/api/v1/ai/*` works without real LLM keys."""

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        reasoning_effort: str,
    ) -> LLMResponse:
        _ = (model, max_tokens, reasoning_effort)
        last_user = messages[-1]["content"] if messages else ""
        lower = last_user.lower()

        mode: str = "create_task"
        if "summary" in lower:
            mode = "summary"
        elif "prioritize" in lower:
            mode = "prioritize"

        priority: str = "medium"
        if "urgent" in lower:
            priority = "urgent"
        elif "high" in lower:
            priority = "high"

        title = last_user.strip()
        if len(title) > 80:
            title = title[:80]
        if not title:
            title = "AI suggested task"

        if mode == "summary":
            content = json.dumps({"mode": "summary", "summary": f"Summary: {title}"})
            return LLMResponse(
                content=content,
                model_used="deterministic",
                tokens_input=1,
                tokens_output=1,
                cache_read_tokens=0,
                latency_ms=0,
            )

        if mode == "prioritize":
            content = json.dumps(
                {
                    "mode": "prioritize",
                    "priorities": ["Review inbox", "Pick top deadline", "Estimate effort"],
                }
            )
            return LLMResponse(
                content=content,
                model_used="deterministic",
                tokens_input=1,
                tokens_output=1,
                cache_read_tokens=0,
                latency_ms=0,
            )

        due_date = None
        if priority in {"high", "urgent"}:
            due_date = (date.today() + timedelta(days=1)).isoformat()

        content = json.dumps(
            {
                "mode": "create_task",
                "task_draft": {"title": title, "priority": priority, "due_date": due_date},
            }
        )
        return LLMResponse(
            content=content,
            model_used="deterministic",
            tokens_input=1,
            tokens_output=1,
            cache_read_tokens=0,
            latency_ms=0,
        )
