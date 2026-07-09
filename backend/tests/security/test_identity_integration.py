"""MVP 5 identity integration tests (TF-054)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.kernel.identity_manager import IdentityManager
from backend.kernel.tool_manager import ToolManager
from backend.security.delegation import create_delegation
from backend.security.nhi_registry import NHIRegistry
from backend.security.vault import CredentialBroker


class _StubMCP:
    def __init__(self) -> None:
        self.last_params: dict[str, object] | None = None

    async def call_tool(self, tool: str, params: dict[str, object]) -> list[dict[str, str]]:
        self.last_params = params
        _ = tool
        return [{"id": "1", "title": "Task"}]


class _Consent:
    async def has_consent(self, user_id, workspace_id) -> bool:  # type: ignore[no-untyped-def]
        _ = (user_id, workspace_id)
        return True


@pytest.mark.asyncio
async def test_full_identity_chain_jwt_delegation_broker_mcp() -> None:
    """JWT user → delegation → broker credential → MCP mock."""
    user_id = uuid4()
    workspace_id = uuid4()
    trace_id = "a" * 32

    identity = IdentityManager()
    delegation = await identity.create_delegation_context(
        user_id=user_id,
        agent_id="context_agent",
        intent="read_tasks",
        session_id=f"{user_id}:{workspace_id}",
        parent_trace_id=trace_id,
    )
    identity.validate_delegation_context(delegation, tool="tasks.list")

    broker = CredentialBroker(mode="memory")
    cred = await broker.get_credential(
        user_id=user_id,
        service="supabase",
        intent="read_tasks",
        workspace_id=workspace_id,
        consent_checker=_Consent(),
    )
    assert cred.access_token

    registry = NHIRegistry()
    registry.initialize()
    mcp = _StubMCP()
    tm = ToolManager(
        mcp_client=mcp,
        nhi_validator=registry,
        credential_broker=broker,
        consent_checker=_Consent(),
    )
    result = await tm.execute_tool(
        "context_agent",
        "tasks.list",
        {"user_id": str(user_id), "workspace_id": workspace_id},
        delegation=delegation,
    )
    assert len(result) == 1
    assert mcp.last_params is not None
    assert mcp.last_params.get("access_token") == cred.access_token


def test_delegation_trace_id_propagated() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="s",
        agent_id="context_agent",
        intent="read_tasks",
        parent_trace_id="trace-abc",
    )
    assert ctx.parent_trace_id == "trace-abc"
