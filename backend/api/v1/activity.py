"""Activity timeline routes (TF-016)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.projects import get_project_service  # noqa: F401
from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.schemas.activity import ActivityListResponse
from backend.services.activity_service import ActivityService

router = APIRouter(tags=["activity"])


def get_activity_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ActivityService:
    return ActivityService(session)


@router.get(
    "/projects/{project_id}/activity",
    response_model=ActivityListResponse,
    status_code=status.HTTP_200_OK,
)
async def project_activity(
    project_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ActivityListResponse:
    items, _total = await service.get_project_activity(
        ctx=ctx,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return ActivityListResponse(items=items, limit=limit, offset=offset)


@router.get(
    "/tasks/{task_id}/activity",
    response_model=ActivityListResponse,
    status_code=status.HTTP_200_OK,
)
async def task_activity(
    task_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[ActivityService, Depends(get_activity_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ActivityListResponse:
    items, _total = await service.get_task_activity(
        ctx=ctx,
        task_id=task_id,
        limit=limit,
        offset=offset,
    )
    return ActivityListResponse(items=items, limit=limit, offset=offset)
