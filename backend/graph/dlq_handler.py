"""DLQ graph integration (TF-043)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from backend.logging_config import get_logger
from backend.schemas.dlq import DLQEventCreate
from backend.services.dlq_service import DLQService

logger = get_logger(__name__)


async def persist_dlq_event(
    dlq_service: DLQService,
    *,
    reason: str,
    envelope: dict[str, Any],
    user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    agent_id: str | None = None,
    request_id: UUID | None = None,
) -> None:
    """Persist a DLQ event without crashing the caller graph."""
    event = DLQEventCreate(
        request_id=request_id or uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        reason=reason,  # type: ignore[arg-type]
        envelope_json=envelope,
    )
    await dlq_service.enqueue(event)


def dlq_handler_node(
    *,
    reason: str,
    envelope: dict[str, Any],
    trace_id: str,
) -> dict[str, Any]:
    """Synchronous DLQ routing payload for graph escalation paths."""
    return {
        "status": "failure",
        "trace_id": trace_id,
        "data": {
            "mode": None,
            "task_draft": None,
            "summary": None,
            "priorities": None,
        },
        "metadata": {
            "trace_id": trace_id,
            "consensus_status": "rejected",
            "reason": reason,
            "dlq": True,
            "envelope": envelope,
        },
    }
