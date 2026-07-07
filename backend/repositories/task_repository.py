"""Task data access repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Task
from backend.repositories.base import WorkspaceScopedRepository


class TaskRepository(WorkspaceScopedRepository[Task]):
    """Repository for task persistence and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    async def list_by_project(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks for a project within a workspace."""
        stmt = (
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.project_id == project_id,
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
