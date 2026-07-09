"""Post-graph security persistence: DLQ rows and sealed audit events (TF-E4)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.graph.dlq_handler import persist_dlq_event
from backend.graph.state import TaskFlowGraphState
from backend.logging_config import get_logger
from backend.schemas.dlq import DLQReason
from backend.security.audit_seal import AuditLogWriter
from backend.services.dlq_service import DLQService

logger = get_logger(__name__)

_PERSIST_REASONS: frozenset[DLQReason] = frozenset(
    {
        "security_violation_detected",
        "verification_failed",
        "mcp_timeout",
        "mcp_validation_failed",
        "max_retries_exceeded",
        "failure",
    }
)


def _resolve_dlq_reason(response: dict[str, Any]) -> DLQReason | None:
    metadata = response.get("metadata", {})
    if not isinstance(metadata, dict):
        return None
    raw_reason = metadata.get("reason")
    if isinstance(raw_reason, str) and raw_reason in _PERSIST_REASONS:
        return raw_reason
    if metadata.get("dlq") and isinstance(raw_reason, str):
        return "failure"
    return None


def _build_envelope(state: TaskFlowGraphState, response: dict[str, Any]) -> dict[str, Any]:
    metadata = response.get("metadata", {})
    nested = metadata.get("envelope") if isinstance(metadata, dict) else None
    consensus_status = metadata.get("consensus_status") if isinstance(metadata, dict) else None
    envelope: dict[str, Any] = {
        "trace_id": state["trace_id"],
        "request_id": str(state["request_id"]),
        "nl_input": state["nl_input"],
        "status": response.get("status"),
        "consensus_status": consensus_status,
    }
    if isinstance(nested, dict):
        envelope.update(nested)
    return envelope


async def persist_graph_outcome(
    session: AsyncSession,
    state: TaskFlowGraphState,
    response: dict[str, Any],
    *,
    agent_id: str | None = None,
) -> None:
    """Persist DLQ events and sealed audit records for graph outcomes."""
    reason = _resolve_dlq_reason(response)
    audit_writer = AuditLogWriter(session)
    user_id: UUID | None = state.get("user_id")
    workspace_id: UUID | None = state.get("workspace_id")
    request_id: UUID = state["request_id"]

    if reason is not None and response.get("status") in {"failure", "degraded"}:
        dlq_service = DLQService(session)
        envelope = _build_envelope(state, response)
        await persist_dlq_event(
            dlq_service,
            reason=reason,
            envelope=envelope,
            user_id=user_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            request_id=request_id,
        )
        if reason == "security_violation_detected":
            await audit_writer.append(
                actor_id=user_id,
                action="security.violation",
                resource_type="ai_request",
                resource_id=request_id,
                metadata={
                    "reason": reason,
                    "trace_id": state["trace_id"],
                    "layer": envelope.get("layer"),
                },
                workspace_id=workspace_id,
            )

    await audit_writer.append(
        actor_id=user_id,
        action="ai.invoked",
        resource_type="ai_request",
        resource_id=request_id,
        metadata={
            "trace_id": state["trace_id"],
            "status": response.get("status"),
            "reason": response.get("metadata", {}).get("reason")
            if isinstance(response.get("metadata"), dict)
            else None,
        },
        workspace_id=workspace_id,
    )
