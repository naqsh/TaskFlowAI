"""DLQ business logic (TF-043)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import ForbiddenError, NotFoundError
from backend.logging_config import get_logger
from backend.metrics import DLQ_ENTRIES_TOTAL
from backend.repositories.dlq_repository import DLQRepository
from backend.schemas.dlq import DLQEventCreate, DLQEventResponse, DLQListResponse
from backend.security.audit_seal import AuditLogWriter

logger = get_logger(__name__)

_SECURITY_REASONS = frozenset({"security_violation_detected"})

GraphRetryFn = Callable[[dict[str, Any], UUID], Awaitable[dict[str, Any]]]


class DLQService:
    def __init__(self, session: AsyncSession, *, max_retries: int = 3) -> None:
        self._repo = DLQRepository(session)
        self._session = session
        self._max_retries = max_retries
        self._audit_writer = AuditLogWriter(session)

    async def enqueue(self, event: DLQEventCreate) -> None:
        try:
            await self._repo.create(event)
            await self._session.commit()
            DLQ_ENTRIES_TOTAL.labels(reason=event.reason).inc()
            await self._audit_writer.append(
                actor_id=event.user_id,
                action="dlq.created",
                resource_type="dlq_event",
                resource_id=event.request_id,
                metadata={"reason": event.reason, "agent_id": event.agent_id},
                workspace_id=event.workspace_id,
            )
        except Exception:
            await self._session.rollback()
            logger.error(
                "dlq_enqueue_failed",
                reason=event.reason,
                request_id=str(event.request_id),
            )

    async def list_events(self, *, limit: int = 50, offset: int = 0) -> DLQListResponse:
        rows, total = await self._repo.list_events(limit=limit, offset=offset)
        items = [
            DLQEventResponse(
                id=row.id,
                request_id=row.request_id,
                user_id=row.user_id,
                workspace_id=row.workspace_id,
                agent_id=row.agent_id,
                reason=row.reason,
                status=row.status,
                envelope_json=row.envelope_json,
                retry_count=row.retry_count,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return DLQListResponse(items=items, total=total, limit=limit, offset=offset)

    async def retry(
        self,
        event_id: UUID,
        *,
        graph_invoke: GraphRetryFn | None = None,
    ) -> dict[str, str]:
        row = await self._repo.get_by_id(event_id)
        if row is None:
            raise NotFoundError("DLQ event not found")

        if row.reason in _SECURITY_REASONS:
            raise ForbiddenError("Security violations cannot be retried")

        if row.retry_count >= self._max_retries:
            await self._repo.mark_permanently_failed(row)
            await self._session.commit()
            raise ForbiddenError("Retry limit exceeded")

        if row.reason != "verification_failed":
            raise ForbiddenError(f"Retry not allowed for reason: {row.reason}")

        await self._repo.mark_retried(row)
        await self._session.commit()
        new_request_id = uuid4()

        if graph_invoke is not None:
            nl_input = row.envelope_json.get("nl_input", "")
            retry_state = {
                "nl_input": nl_input,
                "trace_id": row.envelope_json.get("trace_id", new_request_id.hex),
                "request_id": new_request_id,
                "user_id": row.user_id,
                "workspace_id": row.workspace_id,
            }
            result = await graph_invoke(retry_state, new_request_id)
            return {
                "status": "retry_completed",
                "original_request_id": str(row.request_id),
                "new_request_id": str(new_request_id),
                "graph_status": str(result.get("status", "unknown")),
            }

        return {
            "status": "retry_scheduled",
            "original_request_id": str(row.request_id),
            "new_request_id": str(new_request_id),
        }
