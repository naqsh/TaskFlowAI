"""Notification business logic (TF-013)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Notification, NotificationType
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.exceptions import NotFoundError
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.user_preference_repository import UserPreferenceRepository
from backend.services.audit_service import AuditService
from backend.services.email_service import EmailService


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notifications = NotificationRepository(session)
        self._preferences = UserPreferenceRepository(session)
        self._audit = AuditService()

    async def list_unread(
        self,
        *,
        ctx: WorkspaceAuthContext,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        items = await self._notifications.list_unread_for_user(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.id,
            limit=limit,
            offset=offset,
        )
        total_unread = await self._notifications.count_unread_for_user(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.id,
        )
        return items, total_unread

    async def mark_read(
        self,
        *,
        ctx: WorkspaceAuthContext,
        notification_id: UUID,
    ) -> Notification:
        notification = await self._notifications.get_by_id_for_user_and_workspace(
            notification_id=notification_id,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.id,
        )
        if notification is None:
            raise NotFoundError("Notification not found")

        return await self._notifications.mark_read(notification=notification)

    async def mark_all_read(self, *, ctx: WorkspaceAuthContext) -> int:
        return await self._notifications.mark_all_read(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user.id,
        )

    async def _get_email_enabled(self, *, user_id: UUID) -> bool:
        # For now, default to enabled when preference row doesn't exist.
        pref = await self._preferences.get_by_user_id(user_id=user_id)
        return bool(pref.email_notifications_enabled) if pref else True

    async def notify_task_assigned(
        self,
        *,
        actor_id: UUID | None,
        workspace_id: UUID,
        assignee_id: UUID | None,
        task_id: UUID,
        task_title: str,
    ) -> None:
        if assignee_id is None:
            return

        # Skip emitting notification for self-assignment.
        if actor_id is not None and actor_id == assignee_id:
            return

        notification = Notification(
            workspace_id=workspace_id,
            user_id=assignee_id,
            type=NotificationType.TASK_ASSIGNED.value,
            title="You were assigned a task",
            body=f"{task_title}",
            resource_type="task",
            resource_id=task_id,
            read_at=None,
        )
        self._session.add(notification)
        await self._session.flush()

        await self._audit.log_event(
            actor_id=actor_id,
            action="notification.created",
            resource_type="task",
            resource_id=task_id,
            metadata={
                "notification_type": "task.assigned",
                "recipient_user_id": str(assignee_id),
            },
            workspace_id=workspace_id,
        )

        if await self._get_email_enabled(user_id=assignee_id):
            await EmailService().send_task_assigned(
                actor_id=actor_id,
                recipient_user_id=assignee_id,
                workspace_id=workspace_id,
                task_id=task_id,
                task_title=task_title,
            )

    async def notify_comment_added(
        self,
        *,
        actor_id: UUID | None,
        workspace_id: UUID,
        recipient_user_id: UUID | None,
        task_id: UUID,
        task_title: str,
    ) -> None:
        if recipient_user_id is None:
            return
        if actor_id is not None and actor_id == recipient_user_id:
            return

        notification = Notification(
            workspace_id=workspace_id,
            user_id=recipient_user_id,
            type=NotificationType.COMMENT_ADDED.value,
            title="New comment on your task",
            body=f"{task_title}",
            resource_type="task",
            resource_id=task_id,
            read_at=None,
        )
        self._session.add(notification)
        await self._session.flush()

        await self._audit.log_event(
            actor_id=actor_id,
            action="notification.created",
            resource_type="comment",
            resource_id=task_id,
            metadata={
                "notification_type": "comment.added",
                "recipient_user_id": str(recipient_user_id),
            },
            workspace_id=workspace_id,
        )

    async def notify_due_reminder(
        self,
        *,
        actor_id: UUID | None,
        workspace_id: UUID,
        recipient_user_id: UUID | None,
        task_id: UUID,
        task_title: str,
        due_date: date,
    ) -> None:
        if recipient_user_id is None:
            return

        notification = Notification(
            workspace_id=workspace_id,
            user_id=recipient_user_id,
            type=NotificationType.DUE_REMINDER.value,
            title="Task due soon",
            body=f"{task_title} (due {due_date.isoformat()})",
            resource_type="task",
            resource_id=task_id,
            read_at=None,
        )
        self._session.add(notification)
        await self._session.flush()

        await self._audit.log_event(
            actor_id=actor_id,
            action="notification.created",
            resource_type="task",
            resource_id=task_id,
            metadata={
                "notification_type": "task.due_reminder",
                "recipient_user_id": str(recipient_user_id),
                "due_date": due_date.isoformat(),
            },
            workspace_id=workspace_id,
        )

        if await self._get_email_enabled(user_id=recipient_user_id):
            await EmailService().send_due_reminder(
                actor_id=actor_id,
                recipient_user_id=recipient_user_id,
                workspace_id=workspace_id,
                task_id=task_id,
                task_title=task_title,
                due_date=due_date,
            )
