"""Pydantic schemas for the agentic refactoring loop (ADR-004)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FindingPriority = Literal["high", "medium", "low"]
FindingKind = Literal["rename_symbol", "duplicate_logic", "complexity", "other"]
RunStatus = Literal[
    "reported",
    "awaiting_approval",
    "applying",
    "verified",
    "rolled_back",
    "failed",
]
FeedbackDecision = Literal["accepted", "rejected"]
VerifyOutcome = Literal["pass", "fail", "skipped"]


class RefactorFinding(BaseModel):
    """A prioritized finding with reasoning and a suggested deterministic fix."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    finding_id: str
    priority: FindingPriority
    kind: FindingKind
    reason: str
    file_path: str
    symbol: str | None = None
    line: int | None = None
    suggested_fix: str
    patch_payload: dict[str, Any] = Field(default_factory=dict)


class RefactorPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1)
    description: str


class RefactorRunReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run_id: str
    goal: str
    status: RunStatus
    plan: list[RefactorPlanStep]
    findings: list[RefactorFinding]
    trace_id: str


class ApplyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run_id: str
    status: RunStatus
    applied_finding_ids: list[str]
    changed_files: list[str]
    verify_outcome: VerifyOutcome
    rolled_back: bool
    message: str
    trace_id: str


class FeedbackEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    run_id: str
    finding_id: str | None = None
    decision: FeedbackDecision
    verify_outcome: VerifyOutcome | None = None
    notes: str | None = None
    user_id: UUID | None = None
    workspace_id: UUID | None = None
    trace_id: str
