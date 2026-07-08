from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import nh3

from backend.graph.consensus import ConsensusResult
from backend.graph.state import TaskFlowGraphState
from backend.schemas.envelope import AgentResultEnvelope


def _clean_string(value: str) -> str:
    cleaned = nh3.clean(value)
    return cleaned


def _serialize_date(value: object) -> object:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def orchestrator_present_node(
    state: TaskFlowGraphState,
    *,
    planner: AgentResultEnvelope,
    verification: AgentResultEnvelope,
    adversarial: AgentResultEnvelope,
    critic: AgentResultEnvelope,
    consensus: ConsensusResult,
) -> dict[str, Any]:
    """Compose the final AI response (TF-035)."""

    trace_id = state["trace_id"]

    mode = None
    task_draft: dict[str, Any] | None = None
    summary: str | None = None
    priorities: list[str] | None = None

    if isinstance(planner.result, dict):
        mode = planner.result.get("mode")
        raw_task_draft = planner.result.get("task_draft")
        task_draft = raw_task_draft if isinstance(raw_task_draft, dict) else None

        raw_summary = planner.result.get("summary")
        summary = raw_summary if isinstance(raw_summary, str) else None

        raw_priorities = planner.result.get("priorities")
        priorities = raw_priorities if isinstance(raw_priorities, list) else None

    cleaned_task: dict[str, Any] | None = None
    if task_draft is not None:
        cleaned_task = {}
        for k, v in task_draft.items():
            cleaned_task[k] = _serialize_date(v)
        # Clean title defensively (TF-035 XSS sanitization).
        title = cleaned_task.get("title")
        if isinstance(title, str):
            cleaned_task["title"] = _clean_string(title)

    cleaned_summary = _clean_string(summary) if summary is not None else None
    cleaned_priorities: list[str] | None = None
    if priorities is not None:
        cleaned_priorities = [
            _clean_string(p) if isinstance(p, str) else str(p) for p in priorities
        ]

    # Always emit stable AIResponse keys for frontend Zod contracts (TF-035/TF-040).
    data: dict[str, Any] = {
        "mode": mode,
        "task_draft": cleaned_task,
        "summary": cleaned_summary,
        "priorities": cleaned_priorities,
    }

    total_ms = (
        planner.metadata.execution_ms
        + verification.metadata.execution_ms
        + adversarial.metadata.execution_ms
        + critic.metadata.execution_ms
    )

    # Compose minimal metadata fields required by frontend (TF-040).
    metadata: dict[str, Any] = {
        "trace_id": trace_id,
        "execution_ms": total_ms,
        "tokens_used": (
            planner.metadata.tokens_used
            + verification.metadata.tokens_used
            + adversarial.metadata.tokens_used
            + critic.metadata.tokens_used
        ),
        "model_used": planner.metadata.model_used,
        "prompt_version": planner.metadata.prompt_version,
        "agents_executed": [
            planner.agent_id,
            verification.agent_id,
            adversarial.agent_id,
            critic.agent_id,
        ],
        "cache_hit_rate": None,
        "consensus_status": consensus.status,
        "reason": consensus.reason,
    }

    # Ensure the response is JSON serializable.
    json.dumps(metadata, default=str)
    json.dumps(data, default=str)

    return {"status": "success", "trace_id": trace_id, "data": data, "metadata": metadata}


def orchestrator_handle_escalation_node(
    state: TaskFlowGraphState,
    *,
    consensus: ConsensusResult,
) -> dict[str, Any]:
    """Handle escalation/rejection by returning a safe failure response (TF-035)."""

    trace_id = state["trace_id"]
    status = "failure" if consensus.status in {"rejected"} else "degraded"
    return {
        "status": status,
        "trace_id": trace_id,
        "data": {"mode": None, "task_draft": None, "summary": None, "priorities": None},
        "metadata": {
            "trace_id": trace_id,
            "execution_ms": 0,
            "tokens_used": 0,
            "model_used": None,
            "prompt_version": None,
            "agents_executed": [],
            "cache_hit_rate": None,
            "consensus_status": consensus.status,
            "reason": consensus.reason,
        },
    }


def orchestrator_route_node(state: TaskFlowGraphState) -> dict[str, Any]:
    """Stub route node — selects create_task/summary/prioritize from NL (TF-035)."""

    lower = state["nl_input"].lower()
    if "summary" in lower:
        mode = "summary"
    elif "prioritize" in lower or "what should i work" in lower:
        mode = "prioritize"
    else:
        mode = "create_task"
    return {"mode": mode, "consent_required": False}
