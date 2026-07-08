from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.graph.state import TaskFlowGraphState
from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata


@dataclass(frozen=True)
class Concern:
    severity: str  # "minor" | "major"
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "message": self.message}
        if self.suggestion is not None:
            payload["suggestion"] = self.suggestion
        return payload


def _to_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _extract_task_draft(planner_result: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not planner_result:
        return None
    draft = planner_result.get("task_draft")
    return draft if isinstance(draft, dict) else None


async def adversarial_agent_node(state: TaskFlowGraphState) -> AgentResultEnvelope:
    """Challenge Planner assumptions and find edge cases (TF-032)."""

    start = time.perf_counter()
    trace_id = state["trace_id"]
    user_id = state["user_id"]
    workspace_id = state["workspace_id"]

    planner_result = state.get("planner_result")
    context_result = state.get("context_result")

    concerns: list[Concern] = []

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
            agent_id="adversarial_agent",
            canonical_role="red_team",
            status="escalated",
            result={"concerns": [{"severity": "major", "message": "missing_planner_result"}]},
            metadata=metadata,
            escalation=EscalationPayload(
                reason="adversarial_concerns",
                target_agent="planner",
                context={"planner_result": None},
                retry_allowed=True,
            ),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    mode = planner_result.get("mode")
    if mode == "summary":
        # TF-032 edge: summary mode — flag hallucinated task references not in context.
        summary = planner_result.get("summary")
        if isinstance(summary, str) and "task #" in summary.lower():
            task_ids: set[str] = set()
            if isinstance(context_result, Mapping):
                raw_tasks = context_result.get("tasks")
                if isinstance(raw_tasks, list):
                    for t in raw_tasks:
                        if isinstance(t, Mapping) and t.get("id") is not None:
                            task_ids.add(str(t["id"]))
            if not task_ids:
                concerns.append(
                    Concern(
                        "major",
                        "hallucinated_task_reference_in_summary",
                        suggestion="Only reference task IDs present in context",
                    )
                )
    elif mode == "create_task" or mode is None:
        task_draft = _extract_task_draft(planner_result)
        if task_draft is None:
            concerns.append(
                Concern("major", "task_draft_missing", suggestion="Return a complete task_draft")
            )
        else:
            due_date = _to_date(task_draft.get("due_date"))
            priority = str(task_draft.get("priority") or "").lower()

            today = date.today()
            if due_date is not None and due_date < today:
                concerns.append(
                    Concern(
                        "major",
                        "overdue_due_date_detected",
                        suggestion="Set due_date to a future date",
                    )
                )

            # TF-032: flag unrealistic day-load when >=10 high-priority tasks match same due date.
            if due_date is not None and priority in {"high", "urgent"}:
                tasks = []
                if isinstance(context_result, Mapping):
                    raw_tasks = context_result.get("tasks")
                    if isinstance(raw_tasks, list):
                        tasks = raw_tasks

                match_count = 0
                for t in tasks:
                    if not isinstance(t, Mapping):
                        continue
                    t_due = _to_date(t.get("due_date"))
                    t_pr = str(t.get("priority") or "").lower()
                    if t_due == due_date and t_pr == "high":
                        match_count += 1

                if match_count >= 10:
                    concerns.append(
                        Concern(
                            "major",
                            f"unrealistic_high_workload_due_date_match_count={match_count}",
                            suggestion="Spread HIGH priority work across multiple days",
                        )
                    )

    # TF-032 edge: token limit — prioritize top 3 concerns only.
    concerns = concerns[:3]
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

    major = any(c.severity == "major" for c in concerns)
    if major:
        return AgentResultEnvelope(
            agent_id="adversarial_agent",
            canonical_role="red_team",
            status="escalated",
            result={"concerns": [c.to_dict() for c in concerns]},
            metadata=metadata,
            escalation=EscalationPayload(
                reason="adversarial_concerns",
                target_agent="planner",
                context={"concerns": [c.to_dict() for c in concerns]},
                retry_allowed=True,
            ),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    return AgentResultEnvelope(
        agent_id="adversarial_agent",
        canonical_role="red_team",
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
