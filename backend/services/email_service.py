"""Transactional email stub (TF-017).

This MVP keeps email delivery as an auditable stub to avoid real provider side-effects
while still supporting preference-based enable/disable behavior.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from backend.services.audit_service import AuditService


class EmailService:
    """Email sending interface (stubbed; writes audit events instead)."""

    def __init__(self) -> None:
        self._audit = AuditService()

    async def send_task_assigned(
        self,
        *,
        actor_id: UUID | None,
        recipient_user_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        task_title: str,
    ) -> None:
        await self._audit.log_event(
            actor_id=actor_id,
            action="email.sent",
            resource_type="task",
            resource_id=task_id,
            metadata={
                "email_type": "task_assigned",
                "recipient_user_id": str(recipient_user_id),
                "task_title": task_title,
            },
            workspace_id=workspace_id,
        )

    async def send_due_reminder(
        self,
        *,
        actor_id: UUID | None,
        recipient_user_id: UUID,
        workspace_id: UUID,
        task_id: UUID,
        task_title: str,
        due_date: date,
    ) -> None:
        await self._audit.log_event(
            actor_id=actor_id,
            action="email.sent",
            resource_type="task",
            resource_id=task_id,
            metadata={
                "email_type": "task_due_reminder",
                "recipient_user_id": str(recipient_user_id),
                "task_title": task_title,
                "due_date": due_date.isoformat(),
            },
            workspace_id=workspace_id,
        )
