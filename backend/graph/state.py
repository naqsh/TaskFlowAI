from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict
from uuid import UUID

from backend.security.delegation import DelegationContext

ConsensusStatus = Literal["pending", "agreement", "escalation", "rejected"]


class TaskFlowGraphState(TypedDict, total=False):
    """LangGraph state for TaskFlow AI multi-agent workflows."""

    user_id: UUID
    workspace_id: UUID
    request_id: UUID
    trace_id: str
    nl_input: str

    context_result: dict[str, Any] | None
    planner_result: dict[str, Any] | None
    verification_result: dict[str, Any] | None
    adversarial_result: dict[str, Any] | None
    critic_result: dict[str, Any] | None

    consensus_status: ConsensusStatus | None
    dlq_reason: str | None

    # Allows tools/agents to communicate partial failures without changing the envelope.
    partial: NotRequired[bool]

    # Delegation context propagated API → graph → MCP (TF-049).
    delegation_context: NotRequired[DelegationContext | None]
    session_id: NotRequired[str]
