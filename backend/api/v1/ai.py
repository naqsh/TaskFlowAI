from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import TaskPriority
from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.exceptions import ConsentRequiredError
from backend.graph.factory import build_taskflow_graph
from backend.graph.post_process import persist_graph_outcome
from backend.graph.state import TaskFlowGraphState
from backend.kernel.identity_manager import IdentityManager
from backend.security.identity_factory import build_identity_manager
from backend.services.consent_service import ConsentService
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/ai", tags=["ai"])


class AIParseTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nl_input: str = Field(min_length=1, max_length=10000)


class AISummarizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nl_input: str = Field(min_length=1, max_length=10000)


class AIPrioritizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nl_input: str = Field(min_length=1, max_length=10000)


class AITaskDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    priority: TaskPriority | str
    due_date: str | None = None


class AIResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str | None = None
    task_draft: AITaskDraft | None = None
    summary: str | None = None
    priorities: list[str] | None = None


class AIResponseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    execution_ms: int = Field(ge=0)
    tokens_used: int = Field(ge=0)
    model_used: str | None = None
    prompt_version: str | None = None
    agents_executed: list[str] = Field(default_factory=list)
    cache_hit_rate: float | None = None
    consensus_status: str | None = None
    reason: str | None = None


class AIResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    trace_id: str
    data: AIResponseData
    metadata: AIResponseMetadata


def _session_id(ctx: WorkspaceAuthContext) -> str:
    return f"{ctx.user.id}:{ctx.workspace_id}"


async def _require_ai_consent(
    ctx: WorkspaceAuthContext,
    session: AsyncSession,
) -> None:
    """Enforce workspace-scoped AI consent before graph invoke (TF-051)."""
    consent = ConsentService(session)
    if not await consent.is_valid(user_id=ctx.user.id, workspace_id=ctx.workspace_id):
        raise ConsentRequiredError("AI consent required before invoking AI endpoints")


def _ai_state(
    ctx: WorkspaceAuthContext,
    *,
    trace_id: str,
    nl_input: str,
    identity_manager: IdentityManager,
) -> TaskFlowGraphState:
    session_id = _session_id(ctx)
    delegation = identity_manager.default_for(
        user_id=ctx.user.id,
        agent_id="context_agent",
        intent="read_tasks",
        session_id=session_id,
        parent_trace_id=trace_id,
    )
    return {
        "user_id": ctx.user.id,
        "workspace_id": ctx.workspace_id,
        "request_id": uuid4(),
        "trace_id": trace_id,
        "nl_input": nl_input,
        "session_id": session_id,
        "delegation_context": delegation,
        "context_result": None,
        "planner_result": None,
        "verification_result": None,
        "adversarial_result": None,
        "critic_result": None,
        "consensus_status": None,
        "dlq_reason": None,
        "partial": False,
    }


def _trace_id_from_request(request: Request) -> str:
    incoming = getattr(request.state, "trace_id", None)
    if isinstance(incoming, str) and len(incoming) == 32:
        return incoming
    return request.headers.get("X-Trace-Id", "00000000000000000000000000000000")


def _set_trace_header(response: Response, trace_id: str) -> None:
    response.headers["X-Trace-Id"] = trace_id


async def _run_ai_graph(
    *,
    ctx: WorkspaceAuthContext,
    trace_id: str,
    nl_input: str,
    session: AsyncSession,
    settings: Settings,
) -> dict[str, Any]:
    identity_manager = build_identity_manager(settings)
    graph = build_taskflow_graph(settings, session=session)
    state = _ai_state(
        ctx,
        trace_id=trace_id,
        nl_input=nl_input,
        identity_manager=identity_manager,
    )
    resp_dict = await graph.ainvoke(state)
    await persist_graph_outcome(session, state, resp_dict)
    return resp_dict


@router.post("/parse-task", response_model=AIResponse)
async def parse_task(
    request: Request,
    response: Response,
    payload: AIParseTaskRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIResponse:
    """POST /api/v1/ai/parse-task (TF-037 / TF-051 consent enforced)."""
    await _require_ai_consent(ctx, session)
    trace_id = _trace_id_from_request(request)
    resp_dict = await _run_ai_graph(
        ctx=ctx,
        trace_id=trace_id,
        nl_input=payload.nl_input,
        session=session,
        settings=settings,
    )
    _set_trace_header(response, trace_id)
    return AIResponse.model_validate(resp_dict)


@router.post("/summarize", response_model=AIResponse)
async def summarize(
    request: Request,
    response: Response,
    payload: AISummarizeRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIResponse:
    await _require_ai_consent(ctx, session)
    trace_id = _trace_id_from_request(request)
    nl_input = (
        payload.nl_input
        if "summary" in payload.nl_input.lower()
        else f"{payload.nl_input}\nsummary"
    )
    resp_dict = await _run_ai_graph(
        ctx=ctx,
        trace_id=trace_id,
        nl_input=nl_input,
        session=session,
        settings=settings,
    )
    _set_trace_header(response, trace_id)
    return AIResponse.model_validate(resp_dict)


@router.post("/prioritize", response_model=AIResponse)
async def prioritize(
    request: Request,
    response: Response,
    payload: AIPrioritizeRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIResponse:
    await _require_ai_consent(ctx, session)
    trace_id = _trace_id_from_request(request)
    lower = payload.nl_input.lower()
    if "prioritize" in lower or "what should i work" in lower:
        nl_input = payload.nl_input
    else:
        nl_input = f"{payload.nl_input}\nprioritize"
    resp_dict = await _run_ai_graph(
        ctx=ctx,
        trace_id=trace_id,
        nl_input=nl_input,
        session=session,
        settings=settings,
    )
    _set_trace_header(response, trace_id)
    return AIResponse.model_validate(resp_dict)
