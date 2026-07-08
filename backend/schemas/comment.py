"""Comment request and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Create comment payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    body: str = Field(min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    """Update comment payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    body: str = Field(min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    """Comment resource."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    task_id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime
    updated_at: datetime


class CommentListResponse(BaseModel):
    """Comments for a task."""

    items: list[CommentResponse]
