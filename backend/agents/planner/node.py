from __future__ import annotations

import json
import time
from collections.abc import Mapping
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.db.models import TaskPriority
from backend.graph.state import TaskFlowGraphState
from backend.llm.router import LLMRouter, TokenBudgetExceededError
from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata
from backend.security.input_scanner import InputSecurityScanner, SecurityViolationError
from backend.security.spotlighting import spotlight_external_content


class TaskDraft(BaseModel):
    # LLM JSON may arrive as plain strings; allow Pydantic coercion.
    model_config = ConfigDict(extra="forbid", frozen=True, strict=False)

    title: str = Field(min_length=1, max_length=500)
    # LLM JSON may provide plain strings; accept both enum and raw string.
    priority: TaskPriority | str
    due_date: date | None = None


class PlannerResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=False)

    mode: Literal["create_task", "summary", "prioritize"]
    task_draft: TaskDraft | None = None
    summary: str | None = None
    priorities: list[str] | None = None


def _extract_json_object(text: str) -> str:
    # Handles markdown wrappers: ```json ... ```
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no_json_object_found")
    return text[start : end + 1]


def _infer_mode(nl_input: str) -> Literal["create_task", "summary", "prioritize"]:
    lower = nl_input.lower()
    if "summary" in lower:
        return "summary"
    if "prioritize" in lower or "what should i work" in lower or "today" in lower:
        return "prioritize"
    return "create_task"


async def planner_agent_node(
    state: TaskFlowGraphState,
    llm_router: LLMRouter,
    *,
    scanner: InputSecurityScanner | None = None,
) -> AgentResultEnvelope:
    """Convert a user NL request into structured JSON (Part 1)."""

    start = time.perf_counter()
    scanner = scanner or InputSecurityScanner()

    trace_id = state["trace_id"]
    user_id = state["user_id"]
    workspace_id = state["workspace_id"]

    try:
        scanner.scan_or_raise(state["nl_input"])
    except SecurityViolationError as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        metadata = ExecutionMetadata(
            execution_ms=duration_ms,
            tokens_used=0,
            trace_id=trace_id,
            model_used=None,
            prompt_version=None,
            data_classification="confidential",
            spotlighting_applied=False,
        )
        return AgentResultEnvelope(
            agent_id="planner_agent",
            canonical_role="planner",
            status="escalated",
            result={},
            metadata=metadata,
            escalation=EscalationPayload(
                reason="security_violation_detected",
                target_agent=None,
                context={
                    "matched_pattern": e.scan.matched_pattern,
                    "confidence": e.scan.confidence,
                },
                retry_allowed=False,
            ),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    mode = _infer_mode(state["nl_input"])

    # Prioritize onboarding suggestions when context is empty.
    if mode == "prioritize":
        context = state.get("context_result")
        tasks = (context or {}).get("tasks") if isinstance(context, Mapping) else None
        if not tasks:
            duration_ms = int((time.perf_counter() - start) * 1000)
            metadata = ExecutionMetadata(
                execution_ms=duration_ms,
                tokens_used=0,
                trace_id=trace_id,
                model_used=None,
                prompt_version=None,
                data_classification="confidential",
                spotlighting_applied=True,
            )
            return AgentResultEnvelope(
                agent_id="planner_agent",
                canonical_role="planner",
                status="success",
                result={
                    "mode": "prioritize",
                    "priorities": ["Review inbox", "Pick top deadline", "Estimate effort"],
                },
                metadata=metadata,
                escalation=EscalationPayload(
                    reason=None, target_agent=None, context=None, retry_allowed=False
                ),
                user_id=user_id,
                workspace_id=workspace_id,
            )

    prompt_input = spotlight_external_content(state["nl_input"])
    messages: list[dict[str, str]] = [{"role": "user", "content": prompt_input}]

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            llm_start = time.perf_counter()
            resp = await llm_router.generate(
                messages=messages,
                model="gpt-5.5",
                max_tokens=1024,
                reasoning_effort="high",
                effort="xhigh",
            )
            _ = llm_start
            extracted = _extract_json_object(resp.content)
            parsed = json.loads(extracted)
            validated = PlannerResult.model_validate(parsed)

            duration_ms = int((time.perf_counter() - start) * 1000)
            metadata = ExecutionMetadata(
                execution_ms=duration_ms,
                tokens_used=resp.tokens_input + resp.tokens_output,
                trace_id=trace_id,
                model_used=resp.model_used,
                prompt_version="v2.0.0",
                data_classification="confidential",
                spotlighting_applied=True,
            )

            return AgentResultEnvelope(
                agent_id="planner_agent",
                canonical_role="planner",
                status="success",
                result=validated.model_dump(),
                metadata=metadata,
                escalation=EscalationPayload(
                    reason=None, target_agent=None, context=None, retry_allowed=False
                ),
                user_id=user_id,
                workspace_id=workspace_id,
            )
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = e
            if attempt == 1:
                duration_ms = int((time.perf_counter() - start) * 1000)
                metadata = ExecutionMetadata(
                    execution_ms=duration_ms,
                    tokens_used=0,
                    trace_id=trace_id,
                    model_used=None,
                    prompt_version="v2.0.0",
                    data_classification="confidential",
                    spotlighting_applied=True,
                )
                return AgentResultEnvelope(
                    agent_id="planner_agent",
                    canonical_role="planner",
                    status="escalated",
                    result={},
                    metadata=metadata,
                    escalation=EscalationPayload(
                        reason="verification_failed",
                        target_agent=None,
                        context={"error": str(last_error)},
                        retry_allowed=False,
                    ),
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
        except TokenBudgetExceededError:
            duration_ms = int((time.perf_counter() - start) * 1000)
            metadata = ExecutionMetadata(
                execution_ms=duration_ms,
                tokens_used=0,
                trace_id=trace_id,
                model_used=None,
                prompt_version="v2.0.0",
                data_classification="confidential",
                spotlighting_applied=True,
            )
            return AgentResultEnvelope(
                agent_id="planner_agent",
                canonical_role="planner",
                status="escalated",
                result={},
                metadata=metadata,
                escalation=EscalationPayload(
                    reason="max_retries_exceeded",
                    target_agent=None,
                    context=None,
                    retry_allowed=False,
                ),
                user_id=user_id,
                workspace_id=workspace_id,
            )

    raise RuntimeError("planner_agent_node exhausted retries")
