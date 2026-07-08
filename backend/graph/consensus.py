from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.graph.state import TaskFlowGraphState
from backend.schemas.envelope import AgentResultEnvelope


@dataclass(frozen=True)
class ConsensusResult:
    status: str  # "agreement" | "escalation" | "rejected"
    reason: str | None
    retry_allowed: bool
    constraints: dict[str, Any] | None = None


def _extract_escalation_reason(env: AgentResultEnvelope | None) -> str | None:
    if env is None or env.status != "escalated":
        return None
    return env.escalation.reason


def _concerns_from(env: AgentResultEnvelope | None) -> list[Any] | None:
    if env is None or not isinstance(env.result, dict):
        return None
    concerns = env.result.get("concerns")
    return concerns if isinstance(concerns, list) else None


def evaluate_consensus(
    *,
    verification: AgentResultEnvelope | None,
    adversarial: AgentResultEnvelope | None,
    critic: AgentResultEnvelope | None,
    state: TaskFlowGraphState | None = None,
) -> ConsensusResult:
    """Deterministic consensus aggregator (TF-034).

    Priority: security > verification > adversarial > missing-agent (mcp_timeout).
    """

    _ = state

    # Missing agent result in state => treat as mcp_timeout escalation (TF-034 edge case).
    if verification is None or adversarial is None or critic is None:
        return ConsensusResult(
            status="escalation",
            reason="mcp_timeout",
            retry_allowed=False,
            constraints=None,
        )

    critic_reason = _extract_escalation_reason(critic)
    if critic_reason == "security_violation_detected":
        return ConsensusResult(
            status="rejected",
            reason="security_violation_detected",
            retry_allowed=False,
            constraints=None,
        )

    verification_reason = _extract_escalation_reason(verification)
    if verification_reason == "verification_failed":
        concerns = _concerns_from(verification)
        return ConsensusResult(
            status="escalation",
            reason="verification_failed",
            retry_allowed=True,
            constraints={"concerns": concerns} if concerns is not None else None,
        )

    adversarial_reason = _extract_escalation_reason(adversarial)
    if adversarial_reason == "adversarial_concerns":
        concerns = _concerns_from(adversarial)
        return ConsensusResult(
            status="escalation",
            reason="adversarial_concerns",
            retry_allowed=True,
            constraints={"concerns": concerns} if concerns is not None else None,
        )

    return ConsensusResult(status="agreement", reason=None, retry_allowed=False, constraints=None)
