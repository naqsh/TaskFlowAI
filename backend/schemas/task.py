"""Task request and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.db.models import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    """Create task payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    assignee_id: UUID | None = None


class TaskUpdate(BaseModel):
    """Update task payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assignee_id: UUID | None = None


class TaskResponse(BaseModel):
    """Task resource with optional response metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    assignee_id: UUID | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    warnings: list[str] = Field(default_factory=list)


class TaskListResponse(BaseModel):
    """Paginated task list."""

    items: list[TaskResponse]
    limit: int
    offset: int
