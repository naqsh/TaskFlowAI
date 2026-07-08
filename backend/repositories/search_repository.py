"""Workspace-scoped search queries (TF-015)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Comment, Project, Task, TaskPriority, TaskStatus


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_tasks(
        self,
        *,
        workspace_id: UUID,
        q: str | None,
        project_id: UUID | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: UUID | None,
        due_before: date | None,
        due_after: date | None,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> list[Task]:
        stmt = select(Task).where(Task.workspace_id == workspace_id)

        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        if due_before is not None:
            stmt = stmt.where(Task.due_date.is_not(None), Task.due_date <= due_before)
        if due_after is not None:
            stmt = stmt.where(Task.due_date.is_not(None), Task.due_date >= due_after)
        if not include_archived:
            stmt = stmt.where(Task.status != TaskStatus.ARCHIVED)

        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_projects(
        self,
        *,
        workspace_id: UUID,
        q: str | None,
        project_id: UUID | None,
        include_archived: bool,  # ignored for projects
        limit: int,
        offset: int,
    ) -> list[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id)
        if project_id is not None:
            stmt = stmt.where(Project.id == project_id)

        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(Project.name.ilike(pattern), Project.description.ilike(pattern)))

        stmt = stmt.order_by(Project.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_comments(
        self,
        *,
        workspace_id: UUID,
        q: str | None,
        project_id: UUID | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: UUID | None,
        due_before: date | None,
        due_after: date | None,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> list[Comment]:
        # Search comment bodies while joining their tasks so task filters apply.
        stmt = (
            select(Comment)
            .join(Task, Comment.task_id == Task.id)
            .where(Comment.workspace_id == workspace_id)
        )

        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        if due_before is not None:
            stmt = stmt.where(Task.due_date.is_not(None), Task.due_date <= due_before)
        if due_after is not None:
            stmt = stmt.where(Task.due_date.is_not(None), Task.due_date >= due_after)
        if not include_archived:
            stmt = stmt.where(Task.status != TaskStatus.ARCHIVED)

        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(Comment.body.ilike(pattern))

        stmt = stmt.order_by(Comment.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
