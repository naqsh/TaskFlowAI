from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.kernel.errors import (
    MCPTimeoutError,
    MCPValidationError,
    ToolChainLimitExceeded,
    ToolNotAllowedError,
)
from backend.kernel.tool_manager import ToolManager


class DummyMcpClient:
    def __init__(self, *, sleep_seconds: float = 0.0, response: Any = None) -> None:
        self._sleep_seconds = sleep_seconds
        self._response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, tool: str, params: dict[str, Any]) -> Any:
        self.calls.append((tool, params))
        if self._sleep_seconds:
            await asyncio.sleep(self._sleep_seconds)
        return self._response


class DummyValidator:
    def __init__(self, *, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    def validate(self, tool: str, response: Any) -> Any:
        if self._should_fail:
            raise ValueError("bad response")
        return response


@pytest.mark.asyncio
async def test_tool_manager_rejects_disallowed_tool() -> None:
    mcp = DummyMcpClient(response=[])
    tm = ToolManager(mcp_client=mcp, allowlist={"context_agent": ["tasks.list"]})

    with pytest.raises(ToolNotAllowedError):
        await tm.execute_tool("context_agent", "projects.list", {"workspace_id": "x"})


@pytest.mark.asyncio
async def test_tool_manager_chain_limit_exceeded() -> None:
    mcp = DummyMcpClient(response=[])
    tm = ToolManager(mcp_client=mcp, max_chain_calls=3)

    for _ in range(3):
        await tm.execute_tool("context_agent", "tasks.list", {"workspace_id": "x"})

    with pytest.raises(ToolChainLimitExceeded):
        await tm.execute_tool("context_agent", "tasks.list", {"workspace_id": "x"})


@pytest.mark.asyncio
async def test_tool_manager_timeout_raises() -> None:
    mcp = DummyMcpClient(sleep_seconds=0.05, response=[])
    tm = ToolManager(mcp_client=mcp, timeout_seconds=0.01)

    with pytest.raises(MCPTimeoutError):
        await tm.execute_tool("context_agent", "tasks.list", {"workspace_id": "x"})


@pytest.mark.asyncio
async def test_tool_manager_validator_error_wrapped() -> None:
    mcp = DummyMcpClient(response={"unexpected": "shape"})
    tm = ToolManager(mcp_client=mcp, validator=DummyValidator(should_fail=True))

    with pytest.raises(MCPValidationError):
        await tm.execute_tool("context_agent", "tasks.list", {"workspace_id": "x"})
