"""Activity timeline logic (TF-016)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.rbac import WorkspaceAuthContext
from backend.repositories.activity_repository import ActivityRepository
from backend.repositories.project_repository import ProjectRepository
from backend.repositories.task_repository import TaskRepository
from backend.schemas.activity import ActivityEvent
from backend.security.abac import Action, Resource, check_permission


class ActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = ActivityRepository(session)
        self._tasks = TaskRepository(session)
        self._projects = ProjectRepository(session)

    @staticmethod
    def _summarize(action: str) -> str:
        if action == "task.created":
            return "Task created"
        if action == "task.updated":
            return "Task updated"
        if action == "task.deleted":
            return "Task archived"
        if action == "comment.created":
            return "Comment added"
        if action == "attachment.uploaded":
            return "Attachment uploaded"
        if action == "notification.created":
            return "Notification created"
        return action

    async def get_project_activity(
        self,
        *,
        ctx: WorkspaceAuthContext,
        project_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[ActivityEvent], int]:
        if not check_permission(ctx.role, Resource.PROJECT, Action.READ, actor_id=ctx.user.id):
            return ([], 0)

        project = await self._projects.get_by_id_for_workspace(project_id, ctx.workspace_id)
        if project is None:
            return ([], 0)

        tasks = await self._tasks.list_by_project(
            ctx.workspace_id,
            project_id,
            limit=500,
            offset=0,
        )
        task_ids = {t.id for t in tasks}

        actions = [
            "task.created",
            "task.updated",
            "task.deleted",
            "comment.created",
            "attachment.uploaded",
            "notification.created",
        ]
        recent = await self._audit.list_recent_audit_events(
            workspace_id=ctx.workspace_id,
            action_filter=actions,
            limit=200,
        )

        included: list[ActivityEvent] = []
        for log in recent:
            if log.resource_type == "task":
                if log.resource_id in task_ids:
                    included.append(
                        ActivityEvent(
                            id=log.id,
                            actor_id=log.actor_id,
                            action=log.action,
                            resource_type=log.resource_type,
                            resource_id=log.resource_id,
                            summary=self._summarize(log.action),
                            created_at=log.created_at,
                        )
                    )
                continue

            task_id_value = log.metadata_.get("task_id")
            if task_id_value is None:
                continue
            try:
                task_id = UUID(str(task_id_value))
            except Exception:
                continue
            if task_id in task_ids:
                included.append(
                    ActivityEvent(
                        id=log.id,
                        actor_id=log.actor_id,
                        action=log.action,
                        resource_type=log.resource_type,
                        resource_id=log.resource_id,
                        summary=self._summarize(log.action),
                        created_at=log.created_at,
                    )
                )

        total = len(included)
        sliced = included[offset : offset + limit]
        return sliced, total

    async def get_task_activity(
        self,
        *,
        ctx: WorkspaceAuthContext,
        task_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[ActivityEvent], int]:
        if not check_permission(ctx.role, Resource.TASK, Action.READ, actor_id=ctx.user.id):
            return ([], 0)

        actions = [
            "task.created",
            "task.updated",
            "task.deleted",
            "comment.created",
            "attachment.uploaded",
            "notification.created",
        ]
        recent = await self._audit.list_recent_audit_events(
            workspace_id=ctx.workspace_id,
            action_filter=actions,
            limit=200,
        )

        included: list[ActivityEvent] = []
        for log in recent:
            if log.resource_type == "task" and log.resource_id == task_id:
                included.append(
                    ActivityEvent(
                        id=log.id,
                        actor_id=log.actor_id,
                        action=log.action,
                        resource_type=log.resource_type,
                        resource_id=log.resource_id,
                        summary=self._summarize(log.action),
                        created_at=log.created_at,
                    )
                )
                continue

            task_id_value = log.metadata_.get("task_id")
            if task_id_value is None:
                continue
            try:
                parsed = UUID(str(task_id_value))
            except Exception:
                continue
            if parsed == task_id:
                included.append(
                    ActivityEvent(
                        id=log.id,
                        actor_id=log.actor_id,
                        action=log.action,
                        resource_type=log.resource_type,
                        resource_id=log.resource_id,
                        summary=self._summarize(log.action),
                        created_at=log.created_at,
                    )
                )

        total = len(included)
        sliced = included[offset : offset + limit]
        return sliced, total
