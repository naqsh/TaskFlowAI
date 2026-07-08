"""Notification routes (TF-013)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.schemas.notification import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationListResponse,
)
from backend.services.notification_service import NotificationService

router = APIRouter(tags=["notifications"])


def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationService:
    return NotificationService(session)


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
)
async def list_notifications(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListResponse:
    items, total_unread = await service.list_unread(ctx=ctx, limit=limit, offset=offset)
    return NotificationListResponse(
        items=items,
        total_unread=total_unread,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=MarkReadResponse,
)
async def mark_notification_read(
    notification_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> MarkReadResponse:
    notification = await service.mark_read(ctx=ctx, notification_id=notification_id)
    return MarkReadResponse(notification=notification)


@router.post(
    "/notifications/read-all",
    response_model=MarkAllReadResponse,
)
async def mark_all_notifications_read(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> MarkAllReadResponse:
    updated = await service.mark_all_read(ctx=ctx)
    return MarkAllReadResponse(updated=updated)
