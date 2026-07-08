"""Recent audit-log event retrieval for activity timelines (TF-016)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AuditLog


class ActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent_audit_events(
        self,
        *,
        workspace_id: UUID,
        action_filter: list[str],
        limit: int,
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id, AuditLog.action.in_(action_filter))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
