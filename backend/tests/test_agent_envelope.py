from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata


def test_agent_result_envelope_happy_path() -> None:
    trace_id = uuid4().hex
    envelope = AgentResultEnvelope(
        agent_id="planner-1",
        canonical_role="planner",
        status="success",
        result={"task_draft": {"title": "x"}},
        metadata=ExecutionMetadata(execution_ms=1, tokens_used=10, trace_id=trace_id),
        escalation=EscalationPayload(reason=None, retry_allowed=False),
        user_id=uuid4(),
        workspace_id=uuid4(),
    )
    assert envelope.metadata.trace_id == trace_id


def test_agent_result_envelope_rejects_negative_tokens() -> None:
    trace_id = uuid4().hex
    with pytest.raises(ValidationError):
        AgentResultEnvelope(
            agent_id="planner-1",
            canonical_role="planner",
            status="success",
            result={},
            metadata=ExecutionMetadata(execution_ms=1, tokens_used=-1, trace_id=trace_id),
            escalation=EscalationPayload(reason=None, retry_allowed=False),
            user_id=uuid4(),
            workspace_id=uuid4(),
        )


def test_agent_result_envelope_is_frozen() -> None:
    trace_id = uuid4().hex
    envelope = AgentResultEnvelope(
        agent_id="planner-1",
        canonical_role="planner",
        status="success",
        result={},
        metadata=ExecutionMetadata(execution_ms=1, tokens_used=10, trace_id=trace_id),
        escalation=EscalationPayload(reason=None, retry_allowed=False),
        user_id=uuid4(),
        workspace_id=uuid4(),
    )

    # Pydantic "frozen" models raise a ValidationError on mutation.
    with pytest.raises(ValidationError):
        envelope.metadata.tokens_used = 999  # type: ignore[misc]
