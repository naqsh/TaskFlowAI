from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AgentCanonicalRole = Literal[
    "tool_operator", "planner", "verifier", "red_team", "critic", "supervisor"
]

AgentRunStatus = Literal["success", "escalated", "failed"]

EscalationReason = Literal[
    "security_violation_detected",
    "verification_failed",
    "adversarial_concerns",
    "mcp_timeout",
    "max_retries_exceeded",
    "consent_required",
]


class ExecutionMetadata(BaseModel):
    """Execution metadata attached to every agent result."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    execution_ms: int = Field(ge=0)
    tokens_used: int = Field(ge=0)
    trace_id: str

    model_used: str | None = None
    prompt_version: str | None = None
    data_classification: str | None = None
    spotlighting_applied: bool | None = None


class EscalationPayload(BaseModel):
    """Details about why a graph run escalated or failed."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    reason: EscalationReason | None = None
    target_agent: AgentCanonicalRole | None = None
    context: dict[str, Any] | None = None
    retry_allowed: bool = False


class AgentResultEnvelope(BaseModel):
    """Strict, immutable envelope returned by every agent node."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    # Stable identity for graph routing/debugging.
    agent_id: str
    canonical_role: AgentCanonicalRole

    status: AgentRunStatus

    # The actual agent output (must be JSON-serializable).
    result: dict[str, Any]

    metadata: ExecutionMetadata
    escalation: EscalationPayload

    # Helpful tenant debugging only; not used for auth.
    user_id: UUID | None = None
    workspace_id: UUID | None = None
