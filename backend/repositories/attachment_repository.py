"""Attachment persistence/retrieval (TF-014)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Attachment


class AttachmentRepository:
    """Repository for workspace-scoped attachments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: UUID) -> Attachment | None:
        return await self._session.get(Attachment, attachment_id)

    async def get_by_id_for_workspace(
        self, *, attachment_id: UUID, workspace_id: UUID
    ) -> Attachment | None:
        stmt = select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.workspace_id == workspace_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_task(
        self,
        *,
        workspace_id: UUID,
        task_id: UUID,
        limit: int,
        offset: int,
    ) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(Attachment.workspace_id == workspace_id, Attachment.task_id == task_id)
            .order_by(Attachment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
