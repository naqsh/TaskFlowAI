"""Due date reminder runner (TF-017).

YOLO: provides a manual scan endpoint/service for due tasks due on a given date.
In production this can be invoked daily by a background scheduler/cron.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.rbac import WorkspaceAuthContext
from backend.exceptions import ForbiddenError
from backend.repositories.task_repository import TaskRepository
from backend.services.notification_service import NotificationService


class DueReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self._tasks = TaskRepository(session)
        self._notifications = NotificationService(session)

    async def run_for_workspace(
        self,
        *,
        ctx: WorkspaceAuthContext,
        due_date: date,
    ) -> int:
        # Any member can read tasks; for YOLO we allow run. If you want "cron-only",
        # enforce role == manager/admin here.
        if ctx.role is None:
            raise ForbiddenError("Missing role")

        tasks = await self._tasks.list_due_reminder_tasks(
            ctx.workspace_id,
            due_date=due_date,
            limit=50,
            offset=0,
        )
        sent_or_queued = 0
        for task in tasks:
            await self._notifications.notify_due_reminder(
                actor_id=None,
                workspace_id=ctx.workspace_id,
                recipient_user_id=task.assignee_id,
                task_id=task.id,
                task_title=task.title,
                due_date=due_date,
            )
            sent_or_queued += 1
        return sent_or_queued
