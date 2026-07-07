"""Workspace membership data access."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import WorkspaceMember
from backend.repositories.base import AsyncRepository


class WorkspaceMemberRepository(AsyncRepository[WorkspaceMember]):
    """Repository for workspace membership lookups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspaceMember)

    async def get_membership(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> WorkspaceMember | None:
        """Fetch active membership for a user in a workspace."""
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
