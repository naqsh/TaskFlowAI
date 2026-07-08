"""Admin DLQ API (TF-043)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import WorkspaceRole
from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, require_role
from backend.graph.factory import build_taskflow_graph
from backend.graph.post_process import persist_graph_outcome
from backend.graph.state import TaskFlowGraphState
from backend.schemas.dlq import DLQListResponse
from backend.services.dlq_service import DLQService
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/dlq", tags=["dlq"])


@router.get("", response_model=DLQListResponse)
async def list_dlq_events(
    _ctx: Annotated[WorkspaceAuthContext, Depends(require_role(WorkspaceRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DLQListResponse:
    service = DLQService(session, max_retries=settings.dlq_max_retries)
    return await service.list_events(limit=limit, offset=offset)


@router.post("/{event_id}/retry")
async def retry_dlq_event(
    event_id: UUID,
    ctx: Annotated[WorkspaceAuthContext, Depends(require_role(WorkspaceRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    service = DLQService(session, max_retries=settings.dlq_max_retries)

    async def graph_invoke(retry_state: dict[str, Any], new_request_id: UUID) -> dict[str, Any]:
        graph = build_taskflow_graph(settings, session=session)
        state: TaskFlowGraphState = {
            "user_id": retry_state.get("user_id") or ctx.user.id,
            "workspace_id": retry_state.get("workspace_id") or ctx.workspace_id,
            "request_id": new_request_id,
            "trace_id": str(retry_state.get("trace_id", new_request_id.hex)),
            "nl_input": str(retry_state.get("nl_input", "")),
            "context_result": None,
            "planner_result": None,
            "verification_result": None,
            "adversarial_result": None,
            "critic_result": None,
            "consensus_status": None,
            "dlq_reason": None,
            "partial": False,
        }
        result = await graph.ainvoke(state)
        await persist_graph_outcome(session, state, result)
        return result

    return await service.retry(event_id, graph_invoke=graph_invoke)
