from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from backend.graph.state import TaskFlowGraphState
from backend.kernel.errors import MCPTimeoutError
from backend.kernel.tool_manager import ToolManager
from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata
from backend.security.spotlighting import spotlight_dict

_PRIORITY_ORDER = {
    "urgent": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _priority_rank(priority: Any) -> int:
    if priority is None:
        return 0
    return int(_PRIORITY_ORDER.get(str(priority).lower(), 0))


def _sort_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Earlier due_date first, then higher priority.
    def key(item: dict[str, Any]) -> tuple[int, int]:
        # None due_date sorts last => rank 1 for None.
        due_date = item.get("due_date")
        has_due = due_date is not None
        due_rank = 0 if has_due else 1
        return (due_rank, -_priority_rank(item.get("priority")))

    return sorted(tasks, key=key)


async def context_agent_node(
    state: TaskFlowGraphState, tool_manager: ToolManager
) -> AgentResultEnvelope:
    """Fetch workspace context via MCP and return an agent envelope."""

    start = time.perf_counter()
    user_id: UUID = state["user_id"]
    workspace_id: UUID = state["workspace_id"]

    tool_params: dict[str, Any] = {"user_id": user_id, "workspace_id": workspace_id}

    try:
        results = await _gather_tools(tool_params=tool_params, tool_manager=tool_manager)
    except MCPTimeoutError:
        duration_ms = int((time.perf_counter() - start) * 1000)
        metadata = ExecutionMetadata(
            execution_ms=duration_ms,
            tokens_used=0,
            trace_id=state["trace_id"],
            model_used=None,
            prompt_version=None,
            data_classification="confidential",
            spotlighting_applied=False,
        )
        return AgentResultEnvelope(
            agent_id="context_agent",
            canonical_role="tool_operator",
            status="escalated",
            result={},
            metadata=metadata,
            escalation=EscalationPayload(
                reason="mcp_timeout", target_agent=None, context=None, retry_allowed=False
            ),
            user_id=user_id,
            workspace_id=workspace_id,
        )

    # Spotlight and sort results.
    tasks = results.get("tasks", [])
    projects = results.get("projects", [])
    comments = results.get("comments", [])

    for t in tasks:
        t.update(spotlight_dict(t, text_fields=["title", "description"]))
    for p in projects:
        p.update(spotlight_dict(p, text_fields=["name", "description"]))
    for c in comments:
        c.update(spotlight_dict(c, text_fields=["body"]))

    tasks_sorted = _sort_tasks(tasks)
    truncated = len(tasks_sorted) > 50
    tasks_sorted = tasks_sorted[:50]

    duration_ms = int((time.perf_counter() - start) * 1000)
    metadata = ExecutionMetadata(
        execution_ms=duration_ms,
        tokens_used=0,
        trace_id=state["trace_id"],
        model_used=None,
        prompt_version=None,
        data_classification="confidential",
        spotlighting_applied=True,
    )

    return AgentResultEnvelope(
        agent_id="context_agent",
        canonical_role="tool_operator",
        status="success",
        result={
            "tasks": tasks_sorted,
            "projects": projects,
            "comments": comments,
            "context_summary": "context fetched via MCP",
            "truncated": truncated,
        },
        metadata=metadata,
        escalation=EscalationPayload(
            reason=None, target_agent=None, context=None, retry_allowed=False
        ),
        user_id=user_id,
        workspace_id=workspace_id,
    )


async def _gather_tools(
    *, tool_params: Mapping[str, Any], tool_manager: ToolManager
) -> dict[str, list[dict[str, Any]]]:
    """Fetch tasks/projects/comments and allow partial failures."""
    # We intentionally run sequentially for MVP determinism; Part 2 can parallelize.
    # If a single tool fails, we return whatever is available.
    out: dict[str, list[dict[str, Any]]] = {"tasks": [], "projects": [], "comments": []}

    for tool, target_key in [
        ("tasks.list", "tasks"),
        ("projects.list", "projects"),
        ("comments.list", "comments"),
    ]:
        try:
            response = await tool_manager.execute_tool(
                agent_id="context_agent",
                tool=tool,
                params=dict(tool_params),
            )
            # Tool manager/validator should already normalize to JSON-friendly dicts.
            out[target_key] = response or []
        except MCPTimeoutError:
            # If timeout occurs, propagate for the whole node (Part 1 requirement).
            raise
        except Exception:
            # Partial MCP failure: keep available data.
            out[target_key] = out.get(target_key, [])

    return out
