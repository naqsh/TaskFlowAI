"""Workspace RBAC smoke routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceContextResponse(BaseModel):
    """Current workspace membership for the authenticated user."""

    workspace_id: str
    user_id: str
    role: str


@router.get("/current", response_model=WorkspaceContextResponse)
async def current_workspace(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
) -> WorkspaceContextResponse:
    """Return the caller's workspace context (RBAC smoke endpoint)."""
    return WorkspaceContextResponse(
        workspace_id=str(ctx.workspace_id),
        user_id=str(ctx.user.id),
        role=ctx.role,
    )
