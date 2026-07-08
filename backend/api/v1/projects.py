"""Project CRUD API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, require_permission
from backend.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from backend.security.abac import Action, Resource
from backend.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

ReadProject = Annotated[
    WorkspaceAuthContext, Depends(require_permission(Resource.PROJECT, Action.READ))
]
CreateProject = Annotated[
    WorkspaceAuthContext, Depends(require_permission(Resource.PROJECT, Action.CREATE))
]
UpdateProject = Annotated[
    WorkspaceAuthContext, Depends(require_permission(Resource.PROJECT, Action.UPDATE))
]
DeleteProject = Annotated[
    WorkspaceAuthContext, Depends(require_permission(Resource.PROJECT, Action.DELETE))
]


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectService:
    return ProjectService(session)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    ctx: ReadProject,
    service: Annotated[ProjectService, Depends(get_project_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectListResponse:
    """List projects in the current workspace."""
    items = await service.list_projects(ctx, limit=limit, offset=offset)
    return ProjectListResponse(items=items, limit=limit, offset=offset)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    ctx: CreateProject,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Create a project in the current workspace."""
    return await service.create_project(ctx, payload)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    ctx: ReadProject,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Get a single project by ID."""
    return await service.get_project(ctx, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    ctx: UpdateProject,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    """Update a project."""
    return await service.update_project(ctx, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    ctx: DeleteProject,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> None:
    """Delete a project and its tasks."""
    await service.delete_project(ctx, project_id)
