"""Task data access repository."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Task, TaskPriority, TaskStatus
from backend.repositories.base import WorkspaceScopedRepository


class TaskRepository(WorkspaceScopedRepository[Task]):
    """Repository for task persistence and workspace-scoped queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    async def list_filtered(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks within a workspace with optional filters."""
        stmt = select(Task).where(Task.workspace_id == workspace_id)

        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)

        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_project(
        self,
        workspace_id: UUID,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks for a project within a workspace."""
        return await self.list_filtered(
            workspace_id,
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

    async def list_due_reminder_tasks(
        self,
        workspace_id: UUID,
        *,
        due_date: date,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks due on a specific date for reminder delivery.

        YOLO scope: for each due task, we notify the assignee (if any) and send email
        when the recipient has email notifications enabled.
        """
        stmt = (
            select(Task)
            .where(
                Task.workspace_id == workspace_id,
                Task.due_date == due_date,
                Task.assignee_id.is_not(None),
                Task.status.not_in([TaskStatus.DONE, TaskStatus.ARCHIVED]),
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
