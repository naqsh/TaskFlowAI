"""Task CRUD API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import TaskPriority, TaskStatus
from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from backend.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaskService:
    return TaskService(session)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[TaskService, Depends(get_task_service)],
    project_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    """List tasks with optional filters."""
    items = await service.list_tasks(
        ctx,
        project_id=project_id,
        status=status_filter,
        priority=priority,
        limit=limit,
        offset=offset,
    )
    return TaskListResponse(items=items, limit=limit, offset=offset)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Create a task in a project."""
    return await service.create_task(ctx, payload)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Get a single task by ID."""
    return await service.get_task(ctx, task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Update a task."""
    return await service.update_task(ctx, task_id, payload)


@router.delete("/{task_id}", response_model=TaskResponse)
async def archive_task(
    task_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskResponse:
    """Soft-delete a task by setting status to archived."""
    return await service.archive_task(ctx, task_id)
