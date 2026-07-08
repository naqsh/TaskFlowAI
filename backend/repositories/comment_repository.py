"""Comment data access repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Comment
from backend.repositories.base import WorkspaceScopedRepository


class CommentRepository(WorkspaceScopedRepository[Comment]):
    """Repository for comment persistence and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Comment)

    async def list_by_task(
        self,
        workspace_id: UUID,
        task_id: UUID,
    ) -> list[Comment]:
        """List comments for a task ordered oldest first."""
        stmt = (
            select(Comment)
            .where(
                Comment.workspace_id == workspace_id,
                Comment.task_id == task_id,
            )
            .order_by(Comment.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
