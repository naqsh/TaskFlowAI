from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any

from backend.graph.state import TaskFlowGraphState
from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata
from backend.security.input_scanner import InputSecurityScanner, SecurityViolationError


def _safe_json_dumps(value: object) -> str:
    # Ensure the scan input is always a string; fallback to `repr` for non-JSON values.
    try:
        return json.dumps(value, default=repr, ensure_ascii=False)
    except Exception:
        return repr(value)


async def critic_agent_node(
    state: TaskFlowGraphState,
    *,
    scanner: InputSecurityScanner | None = None,
) -> AgentResultEnvelope:
    """Final safety and quality gate (TF-033)."""

    start = time.perf_counter()
    trace_id = state["trace_id"]
    user_id = state["user_id"]
    workspace_id = state["workspace_id"]

    scanner = scanner or InputSecurityScanner()

    planner_result = state.get("planner_result")
    context_result = state.get("context_result")

    combined = _safe_json_dumps(
        {"planner_result": planner_result, "context_result": context_result}
    )

    try:
        scanner.scan_or_raise(combined)
    except SecurityViolationError as e:
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
            agent_id="critic_agent",
            canonical_role="critic",
            status="escalated",
            result={"concerns": [{"severity": "major", "message": "security_violation_detected"}]},
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

    # Quality checks (deterministic MVP behavior).
    concerns: list[dict[str, Any]] = []
    if isinstance(planner_result, Mapping):
        mode = planner_result.get("mode")
        if mode == "create_task":
            draft = planner_result.get("task_draft")
            if isinstance(draft, Mapping):
                title = draft.get("title")
                if isinstance(title, str) and len(title.strip()) < 3:
                    concerns.append({"severity": "minor", "message": "vague_title_length_lt_3"})

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
        agent_id="critic_agent",
        canonical_role="critic",
        status="success",
        result={"concerns": concerns},
        metadata=metadata,
        escalation=EscalationPayload(
            reason=None,
            target_agent=None,
            context=None,
            retry_allowed=False,
        ),
        user_id=user_id,
        workspace_id=workspace_id,
    )
