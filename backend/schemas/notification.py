"""Notification schemas (TF-013)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Notification resource returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    type: str
    title: str
    body: str
    resource_type: str
    resource_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated unread notifications list."""

    items: list[NotificationResponse]
    total_unread: int
    limit: int
    offset: int


class MarkReadResponse(BaseModel):
    notification: NotificationResponse


class MarkAllReadResponse(BaseModel):
    updated: int = Field(..., description="Number of notifications marked as read.")
