"""Project data access repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Project
from backend.repositories.base import WorkspaceScopedRepository


class ProjectRepository(WorkspaceScopedRepository[Project]):
    """Repository for project persistence and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_ordered(
        self,
        workspace_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """List projects for a workspace ordered by recency."""
        stmt = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
