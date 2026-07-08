"""Activity timeline schemas (TF-016)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ActivityEvent(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    summary: str
    created_at: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityEvent]
    limit: int
    offset: int
