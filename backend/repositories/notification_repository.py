"""Notification persistence/retrieval (TF-013)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Notification


class NotificationRepository:
    """Repository for user/workspace scoped notification queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_unread_for_user(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_unread_for_user(self, *, workspace_id: UUID, user_id: UUID) -> int:
        stmt = select(Notification.id).where(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return len(list(result.scalars().all()))

    async def get_by_id_for_user_and_workspace(
        self,
        *,
        notification_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_read(self, *, notification: Notification) -> Notification:
        notification.read_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(notification)
        return notification

    async def mark_all_read(self, *, workspace_id: UUID, user_id: UUID) -> int:
        now = datetime.now(UTC)
        stmt = (
            update(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=now)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        # rowcount may be -1 depending on dialect; treat it as best-effort.
        return int(getattr(result, "rowcount", 0) or 0)
