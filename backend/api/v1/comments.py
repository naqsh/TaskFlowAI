"""Comment CRUD API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.schemas.comment import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
)
from backend.services.comment_service import CommentService

router = APIRouter(tags=["comments"])


def get_comment_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CommentService:
    return CommentService(session)


@router.get("/tasks/{task_id}/comments", response_model=CommentListResponse)
async def list_comments(
    task_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentListResponse:
    """List comments on a task."""
    items = await service.list_comments(ctx, task_id)
    return CommentListResponse(items=items)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_id: UUID,
    payload: CommentCreate,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentResponse:
    """Add a comment to a task."""
    return await service.create_comment(ctx, task_id, payload)


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentResponse:
    """Update a comment (author only, within 15 minutes of creation)."""
    return await service.update_comment(ctx, comment_id, payload)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[CommentService, Depends(get_comment_service)],
) -> None:
    """Delete a comment."""
    await service.delete_comment(ctx, comment_id)
