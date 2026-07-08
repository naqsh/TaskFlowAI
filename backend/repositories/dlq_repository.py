"""DLQ persistence repository (TF-043)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import DLQEvent
from backend.schemas.dlq import DLQEventCreate


class DLQRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: DLQEventCreate) -> DLQEvent:
        row = DLQEvent(
            request_id=event.request_id,
            user_id=event.user_id,
            workspace_id=event.workspace_id,
            agent_id=event.agent_id,
            reason=event.reason,
            envelope_json=event.envelope_json,
            retry_count=event.retry_count,
            status="pending",
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, event_id: UUID) -> DLQEvent | None:
        return await self._session.get(DLQEvent, event_id)

    async def list_events(self, *, limit: int, offset: int) -> tuple[list[DLQEvent], int]:
        count_stmt = select(func.count()).select_from(DLQEvent)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = select(DLQEvent).order_by(DLQEvent.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def mark_retried(self, event: DLQEvent) -> DLQEvent:
        event.retry_count += 1
        event.status = "retried"
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def mark_permanently_failed(self, event: DLQEvent) -> DLQEvent:
        event.status = "permanently_failed"
        await self._session.flush()
        await self._session.refresh(event)
        return event
