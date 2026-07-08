from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from backend.db.models import TaskPriority
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.graph.builder import build_taskflow_ai_graph
from backend.graph.state import TaskFlowGraphState
from backend.kernel.tool_manager import ToolManager
from backend.llm.router import LLMProviderProtocol, LLMResponse, LLMRouter
from backend.mcp.postgres_stdio import PostgresMCPClient
from backend.mcp.validator import MCPResponseValidator
from backend.security.input_scanner import InputSecurityScanner

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
    due_date: date | None = None


class AIResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["create_task", "summary", "prioritize"] | None = None
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

    status: Literal["success", "degraded", "failure"]
    trace_id: str
    data: AIResponseData
    metadata: AIResponseMetadata


class _DeterministicPlannerProvider(LLMProviderProtocol):
    """Local fallback provider so `/api/v1/ai/*` works without real LLM keys."""

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        reasoning_effort: str,
    ) -> LLMResponse:
        _ = (model, max_tokens, reasoning_effort)
        last_user = messages[-1]["content"] if messages else ""
        lower = last_user.lower()

        mode: str = "create_task"
        if "summary" in lower:
            mode = "summary"
        elif "prioritize" in lower:
            mode = "prioritize"

        priority: str = "medium"
        if "urgent" in lower:
            priority = "urgent"
        elif "high" in lower:
            priority = "high"

        title = last_user.strip()
        if len(title) > 80:
            title = title[:80]
        if not title:
            title = "AI suggested task"

        if mode == "summary":
            content = json.dumps({"mode": "summary", "summary": f"Summary: {title}"})
            return LLMResponse(
                content=content,
                model_used="deterministic",
                tokens_input=1,
                tokens_output=1,
                cache_read_tokens=0,
                latency_ms=0,
            )

        if mode == "prioritize":
            content = json.dumps(
                {
                    "mode": "prioritize",
                    "priorities": ["Review inbox", "Pick top deadline", "Estimate effort"],
                }
            )
            return LLMResponse(
                content=content,
                model_used="deterministic",
                tokens_input=1,
                tokens_output=1,
                cache_read_tokens=0,
                latency_ms=0,
            )

        due_date = None
        if priority in {"high", "urgent"}:
            due_date = (date.today() + timedelta(days=1)).isoformat()

        content = json.dumps(
            {
                "mode": "create_task",
                "task_draft": {"title": title, "priority": priority, "due_date": due_date},
            }
        )
        return LLMResponse(
            content=content,
            model_used="deterministic",
            tokens_input=1,
            tokens_output=1,
            cache_read_tokens=0,
            latency_ms=0,
        )


def _make_llm_router() -> LLMRouter:
    primary = _DeterministicPlannerProvider()
    return LLMRouter(primary_provider=primary, fallback_provider=None)


def _make_tool_manager() -> ToolManager:
    mcp_client = PostgresMCPClient()
    validator = MCPResponseValidator()
    return ToolManager(mcp_client=mcp_client, validator=validator)


def _build_graph() -> Any:
    # Graph runner uses deterministic planner provider by default.
    # Tool sandbox defaults to mock MCP when stdio/npx is unavailable.
    llm_router = _make_llm_router()
    scanner = InputSecurityScanner()
    tool_manager = _make_tool_manager()
    return build_taskflow_ai_graph(
        llm_router=llm_router,
        scanner=scanner,
        tool_manager=tool_manager,
    )


def _ai_state(ctx: WorkspaceAuthContext, *, trace_id: str, nl_input: str) -> TaskFlowGraphState:
    return {
        "user_id": ctx.user.id,
        "workspace_id": ctx.workspace_id,
        "request_id": uuid4(),
        "trace_id": trace_id,
        "nl_input": nl_input,
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


@router.post("/parse-task", response_model=AIResponse)
async def parse_task(
    request: Request,
    response: Response,
    payload: AIParseTaskRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
) -> AIResponse:
    """POST /api/v1/ai/parse-task (TF-037)."""
    # MVP 3: AI consent stub always allowed; enforced in MVP 5 (TF-049).
    ai_consent_granted = True
    if not ai_consent_granted:
        _set_trace_header(response, _trace_id_from_request(request))
        return AIResponse(
            status="failure",
            trace_id=_trace_id_from_request(request),
            data=AIResponseData(mode=None, task_draft=None, summary=None, priorities=None),
            metadata=AIResponseMetadata(
                trace_id=_trace_id_from_request(request),
                execution_ms=0,
                tokens_used=0,
                reason="consent_required",
            ),
        )

    trace_id = _trace_id_from_request(request)
    graph = _build_graph()
    state = _ai_state(ctx, trace_id=trace_id, nl_input=payload.nl_input)
    resp_dict = await graph.ainvoke(state)
    _set_trace_header(response, trace_id)
    return AIResponse.model_validate(resp_dict)


@router.post("/summarize", response_model=AIResponse)
async def summarize(
    request: Request,
    response: Response,
    payload: AISummarizeRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
) -> AIResponse:
    graph = _build_graph()
    trace_id = _trace_id_from_request(request)
    nl_input = (
        payload.nl_input
        if "summary" in payload.nl_input.lower()
        else f"{payload.nl_input}\nsummary"
    )
    state = _ai_state(ctx, trace_id=trace_id, nl_input=nl_input)
    resp_dict = await graph.ainvoke(state)
    _set_trace_header(response, trace_id)
    return AIResponse.model_validate(resp_dict)


@router.post("/prioritize", response_model=AIResponse)
async def prioritize(
    request: Request,
    response: Response,
    payload: AIPrioritizeRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
) -> AIResponse:
    graph = _build_graph()
    trace_id = _trace_id_from_request(request)
    lower = payload.nl_input.lower()
    if "prioritize" in lower or "what should i work" in lower:
        nl_input = payload.nl_input
    else:
        nl_input = f"{payload.nl_input}\nprioritize"
    state = _ai_state(ctx, trace_id=trace_id, nl_input=nl_input)
    resp_dict = await graph.ainvoke(state)
    _set_trace_header(response, trace_id)
    return AIResponse.model_validate(resp_dict)
