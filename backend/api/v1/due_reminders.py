"""Due date reminder runner (TF-017).

YOLO: exposes a manual endpoint to trigger due reminder scanning for tasks due
on a specified date. In production this can be called daily by a scheduler.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.services.due_reminder_service import DueReminderService

router = APIRouter(prefix="/collaboration/due-reminders", tags=["due-reminders"])


def get_due_reminder_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DueReminderService:
    return DueReminderService(session)


@router.post("/run")
async def run_due_reminders(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[DueReminderService, Depends(get_due_reminder_service)],
    due_date: Annotated[date | None, Query()] = None,
) -> dict[str, int]:
    # Default: scan tasks due tomorrow (24h before deadline in a "due date" model).
    target_due_date = due_date or (date.today() + timedelta(days=1))
    count = await service.run_for_workspace(ctx=ctx, due_date=target_due_date)
    return {"processed": count}
