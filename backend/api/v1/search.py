"""Search routes (TF-015)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import TaskPriority, TaskStatus
from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.schemas.search import SearchResponse
from backend.services.search_service import SearchService

router = APIRouter(tags=["search"])


def get_search_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SearchService:
    return SearchService(session)


@router.get(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    service: Annotated[SearchService, Depends(get_search_service)],
    q: Annotated[str | None, Query()] = None,
    type: Annotated[str | None, Query(alias="type")] = "tasks",
    project_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    assignee_id: Annotated[UUID | None, Query()] = None,
    due_before: Annotated[date | None, Query()] = None,
    due_after: Annotated[date | None, Query()] = None,
    include_archived: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SearchResponse:
    items, total = await service.search(
        ctx=ctx,
        q=q,
        type_filter=type,
        project_id=project_id,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
        due_before=due_before,
        due_after=due_after,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return SearchResponse(items=items, total=total, q=q or "")
