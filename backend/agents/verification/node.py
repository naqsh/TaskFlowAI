from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.db.models import TaskPriority
from backend.graph.state import TaskFlowGraphState
from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata


@dataclass(frozen=True)
class Concern:
    severity: str  # "minor" | "major"
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "message": self.message}


def _to_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _normalize_priority(value: object) -> TaskPriority | None:
    try:
        return TaskPriority(str(value))
    except Exception:
        return None


def _extract_task_draft(planner_result: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not planner_result:
        return None
    draft = planner_result.get("task_draft")
    return draft if isinstance(draft, dict) else None


async def verification_agent_node(state: TaskFlowGraphState) -> AgentResultEnvelope:
    """Validate Planner output for schema compliance, logic, and completeness (TF-031)."""

    start = time.perf_counter()
    trace_id = state["trace_id"]
    user_id = state["user_id"]
    workspace_id = state["workspace_id"]

    planner_result = state.get("planner_result")
    if not isinstance(planner_result, Mapping):
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
            agent_id="verification_agent",
            canonical_role="verifier",
            status="escalated",
            result={"concerns": [{"severity": "major", "message": "missing_planner_result"}]},
            metadata=metadata,
            escalation=EscalationPayload(
                reason="verification_failed",
                target_agent="planner",
                context={"planner_result": None},
                retry_allowed=True,
            ),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    mode = planner_result.get("mode")
    concerns: list[Concern] = []

    # TF-031 edge case: in summary mode we skip task validation and validate summary completeness.
    if mode == "summary":
        summary = planner_result.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            concerns.append(Concern("major", "summary_missing_or_empty"))

    elif mode == "prioritize":
        priorities = planner_result.get("priorities")
        if (
            not isinstance(priorities, list)
            or not priorities
            or not all(isinstance(p, str) and p.strip() for p in priorities)
        ):
            concerns.append(Concern("major", "priorities_missing_or_invalid"))

    else:
        # Default to create_task validation.
        task_draft = _extract_task_draft(planner_result)
        if task_draft is None:
            concerns.append(Concern("major", "task_draft_missing"))
        else:
            title = task_draft.get("title")
            if not isinstance(title, str) or not title.strip():
                concerns.append(Concern("major", "title_missing_or_empty"))

            priority = task_draft.get("priority")
            normalized_priority = _normalize_priority(priority)
            if normalized_priority is None:
                concerns.append(Concern("major", "priority_invalid"))

            due_date_raw = task_draft.get("due_date")
            due_date = _to_date(due_date_raw)

            # TF-031: due_date required for HIGH priority and must be after today.
            if normalized_priority in {TaskPriority.HIGH, TaskPriority.URGENT}:
                today = date.today()
                if due_date is None:
                    concerns.append(Concern("major", "due_date_required_for_high"))
                elif due_date <= today:
                    concerns.append(Concern("major", "due_date_must_be_in_future"))

    major = any(c.severity == "major" for c in concerns)
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

    if major:
        return AgentResultEnvelope(
            agent_id="verification_agent",
            canonical_role="verifier",
            status="escalated",
            result={"concerns": [c.to_dict() for c in concerns]},
            metadata=metadata,
            escalation=EscalationPayload(
                reason="verification_failed",
                target_agent="planner",
                context={"concerns": [c.to_dict() for c in concerns]},
                retry_allowed=True,
            ),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    return AgentResultEnvelope(
        agent_id="verification_agent",
        canonical_role="verifier",
        status="success",
        result={"concerns": [c.to_dict() for c in concerns]},
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
