"""Confused deputy prevention tests (TF-054)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.kernel.errors import ConfusedDeputyError
from backend.kernel.tool_manager import ToolManager
from backend.security.delegation import create_delegation
from backend.security.nhi_registry import NHIRegistry


class _StubMCP:
    async def call_tool(self, tool: str, params: dict[str, object]) -> list[dict[str, str]]:
        _ = (tool, params)
        return []


@pytest.fixture
def registry() -> NHIRegistry:
    reg = NHIRegistry()
    reg.initialize()
    return reg


@pytest.mark.asyncio
async def test_agent_cannot_escalate_permissions(registry: NHIRegistry) -> None:
    """Agent with read_projects intent cannot call tasks.list."""
    tm = ToolManager(
        mcp_client=_StubMCP(),
        nhi_validator=registry,
    )
    delegation = create_delegation(
        user_id=uuid4(),
        session_id="s1",
        agent_id="context_agent",
        intent="read_projects",
    )
    with pytest.raises(ConfusedDeputyError):
        await tm.execute_tool(
            "context_agent",
            "tasks.list",
            {"workspace_id": str(uuid4())},
            delegation=delegation,
        )


@pytest.mark.asyncio
async def test_agent_id_mismatch_blocked(registry: NHIRegistry) -> None:
    tm = ToolManager(mcp_client=_StubMCP(), nhi_validator=registry)
    delegation = create_delegation(
        user_id=uuid4(),
        session_id="s1",
        agent_id="planner_agent",
        intent="read_tasks",
    )
    with pytest.raises(ConfusedDeputyError, match="agent_id_mismatch"):
        await tm.execute_tool(
            "context_agent",
            "tasks.list",
            {},
            delegation=delegation,
        )


@pytest.mark.asyncio
async def test_valid_delegation_allows_mcp_call(registry: NHIRegistry) -> None:
    tm = ToolManager(mcp_client=_StubMCP(), nhi_validator=registry)
    delegation = create_delegation(
        user_id=uuid4(),
        session_id="s1",
        agent_id="context_agent",
        intent="read_tasks",
    )
    result = await tm.execute_tool(
        "context_agent",
        "tasks.list",
        {},
        delegation=delegation,
    )
    assert result == []
