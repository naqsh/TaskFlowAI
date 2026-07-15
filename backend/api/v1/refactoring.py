"""Agentic refactoring API (ADR-004) — analyze → approve → apply."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import WorkspaceRole
from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, require_role
from backend.exceptions import ConsentRequiredError, ForbiddenError, ValidationError
from backend.refactoring.sandbox import SandboxError
from backend.refactoring.schemas import ApplyResult, FeedbackEvent, RefactorRunReport
from backend.refactoring.service import AgenticRefactoringService
from backend.refactoring.store import get_run_store
from backend.services.consent_service import ConsentService
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/refactoring", tags=["refactoring"])


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    goal: str = Field(min_length=1, max_length=2000)
    symbol: str = Field(min_length=1, max_length=200)
    new_name: str | None = Field(default=None, min_length=1, max_length=200)


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1, max_length=64)
    approved_finding_ids: list[str] = Field(min_length=1, max_length=500)


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1, max_length=64)
    finding_ids: list[str] = Field(min_length=1, max_length=500)
    decision: str = Field(pattern="^(accepted|rejected)$")
    notes: str | None = Field(default=None, max_length=2000)


def _require_refactoring_enabled(settings: Settings) -> None:
    if not settings.refactoring_enabled:
        raise ForbiddenError("Agentic refactoring is disabled (set REFACTORING_ENABLED=true)")
    if not settings.refactoring_sandbox_root.strip():
        raise ForbiddenError("REFACTORING_SANDBOX_ROOT must be configured")


async def _require_ai_consent(ctx: WorkspaceAuthContext, session: AsyncSession) -> None:
    consent = ConsentService(session)
    if not await consent.is_valid(user_id=ctx.user.id, workspace_id=ctx.workspace_id):
        raise ConsentRequiredError("AI consent required before invoking refactoring endpoints")


def _build_service(settings: Settings) -> AgenticRefactoringService:
    return AgenticRefactoringService(
        sandbox_root=settings.refactoring_sandbox_root,
        verify_command=settings.refactoring_verify_command,
        feedback_path=settings.refactoring_feedback_path,
        run_store=get_run_store(),
    )


@router.post("/analyze", response_model=RefactorRunReport)
async def analyze_refactoring(
    body: AnalyzeRequest,
    response: Response,
    ctx: Annotated[WorkspaceAuthContext, Depends(require_role(WorkspaceRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RefactorRunReport:
    """Goal → Plan → Search → Report. No files mutated until /apply."""
    _require_refactoring_enabled(settings)
    await _require_ai_consent(ctx, session)
    trace_id = str(uuid4())
    response.headers["X-Trace-Id"] = trace_id
    service = _build_service(settings)
    try:
        return service.analyze(
            goal=body.goal,
            symbol=body.symbol,
            new_name=body.new_name,
            trace_id=trace_id,
        )
    except SandboxError as exc:
        raise ValidationError(str(exc)) from exc


@router.post("/apply", response_model=ApplyResult)
async def apply_refactoring(
    body: ApplyRequest,
    response: Response,
    ctx: Annotated[WorkspaceAuthContext, Depends(require_role(WorkspaceRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApplyResult:
    """Human-approved findings → Snapshot → Patch → Verify → Rollback on fail."""
    _require_refactoring_enabled(settings)
    await _require_ai_consent(ctx, session)
    trace_id = str(uuid4())
    response.headers["X-Trace-Id"] = trace_id
    service = _build_service(settings)
    try:
        return service.apply(
            run_id=body.run_id,
            approved_finding_ids=body.approved_finding_ids,
            user_id=ctx.user.id,
            workspace_id=ctx.workspace_id,
        )
    except SandboxError as exc:
        raise ValidationError(str(exc)) from exc


@router.post("/feedback")
async def record_feedback(
    body: FeedbackRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(require_role(WorkspaceRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    """Record accept/reject as RL improvement signal (reject path)."""
    _require_refactoring_enabled(settings)
    await _require_ai_consent(ctx, session)
    service = _build_service(settings)
    if body.decision != "rejected":
        # Accepted findings are recorded automatically during /apply.
        return {"recorded": 0, "message": "accepted feedback is recorded on /apply"}
    try:
        count = service.reject_findings(
            run_id=body.run_id,
            finding_ids=body.finding_ids,
            user_id=ctx.user.id,
            workspace_id=ctx.workspace_id,
            notes=body.notes,
        )
    except SandboxError as exc:
        raise ValidationError(str(exc)) from exc
    return {"recorded": count}


@router.get("/runs/{run_id}", response_model=RefactorRunReport)
async def get_refactoring_run(
    run_id: str,
    ctx: Annotated[WorkspaceAuthContext, Depends(require_role(WorkspaceRole.ADMIN))],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RefactorRunReport:
    _require_refactoring_enabled(settings)
    await _require_ai_consent(ctx, session)
    service = _build_service(settings)
    try:
        return service.get_report(run_id)
    except SandboxError as exc:
        raise ValidationError(str(exc)) from exc


# Silence unused import lint if FeedbackEvent unused — keep for OpenAPI docs typing.
_ = FeedbackEvent
