"""API v1 consent endpoints (TF-051)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db
from backend.dependencies.rbac import WorkspaceAuthContext, get_workspace_auth_context
from backend.services.consent_service import CONSENT_SCOPE_AI, ConsentService

router = APIRouter(prefix="/consent", tags=["consent"])


class ConsentGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: str = Field(default=CONSENT_SCOPE_AI, max_length=60)


class ConsentStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    granted: bool
    scope: str
    expires_at: str | None = None


class ConsentGrantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    scope: str
    expires_at: str


@router.post("/ai", response_model=ConsentGrantResponse)
async def grant_ai_consent(
    payload: ConsentGrantRequest,
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConsentGrantResponse:
    """POST /api/v1/consent/ai — grant workspace-scoped AI consent."""
    service = ConsentService(session)
    record = await service.grant(
        user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        scope=payload.scope,
    )
    await session.commit()
    return ConsentGrantResponse(
        status="granted",
        scope=record.scope,
        expires_at=record.expires_at.isoformat(),
    )


@router.delete("/ai", response_model=ConsentStatusResponse)
async def revoke_ai_consent(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConsentStatusResponse:
    """DELETE /api/v1/consent/ai — revoke AI consent immediately."""
    service = ConsentService(session)
    await service.revoke(user_id=ctx.user.id, workspace_id=ctx.workspace_id)
    await session.commit()
    return ConsentStatusResponse(granted=False, scope=CONSENT_SCOPE_AI)


@router.get("/ai", response_model=ConsentStatusResponse)
async def get_ai_consent_status(
    ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConsentStatusResponse:
    """GET /api/v1/consent/ai — check current consent status."""
    service = ConsentService(session)
    record = await service.check_consent(
        user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
    )
    if record is None:
        return ConsentStatusResponse(granted=False, scope=CONSENT_SCOPE_AI)
    return ConsentStatusResponse(
        granted=True,
        scope=record.scope,
        expires_at=record.expires_at.isoformat(),
    )
