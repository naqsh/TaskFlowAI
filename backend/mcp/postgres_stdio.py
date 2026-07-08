from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from backend.mcp.client import MCPClientProtocol
from backend.mcp.stdio_transport import StdioTransport


class MockPostgresMCPClient(MCPClientProtocol):
    """Mock MCP client used by unit tests and local dev without npx."""

    def __init__(self, *, seeded: dict[str, Any] | None = None) -> None:
        self._seeded = seeded or {}

    async def call_tool(self, tool: str, params: dict[str, Any]) -> Any:
        # Keep behavior simple: tool lookup only; params are for RLS defense in depth.
        if tool not in self._seeded:
            return []
        return self._seeded[tool]

    async def request(self, tool: str, params: Mapping[str, Any]) -> Any:
        # StdioTransport-compatible API used by PostgresMCPClient.
        return await self.call_tool(tool=tool, params=dict(params))


class PostgresMCPClient(MCPClientProtocol):
    """PostgreSQL MCP client for read-only context (tasks/projects/comments).

    Part 1 provides structure + validation; actual stdio subprocess spawning
    is out of scope for unit tests.
    """

    _allowed_tools = {"tasks.list", "tasks.read", "projects.list", "comments.list"}

    def __init__(self, transport: StdioTransport | MockPostgresMCPClient | None = None) -> None:
        if transport is not None:
            self._transport = transport
            return

        mode = os.getenv("MCP_TRANSPORT", "mock").lower()
        if mode == "stdio":
            self._transport = StdioTransport()
        else:
            # Default to mock so unit tests and local dev don't require npx.
            self._transport = MockPostgresMCPClient()

    async def call_tool(self, tool: str, params: dict[str, Any]) -> Any:
        if tool not in self._allowed_tools:
            raise ValueError(f"tool_not_allowed tool={tool}")

        self._validate_params(tool=tool, params=params)
        return await self._transport.request(tool=tool, params=params)

    @staticmethod
    def _validate_params(*, tool: str, params: dict[str, Any]) -> None:
        # Defense in depth: every query must bind `user_id` for RLS.
        if "user_id" not in params:
            raise ValueError("missing user_id parameter for RLS defense in depth")

        # If future tools accept raw SQL, prevent unparameterized SQL injection.
        if "sql" in params and isinstance(params["sql"], str):
            sql = params["sql"]
            if ":user_id" not in sql and "$1" not in sql:
                raise ValueError("raw SQL rejected: user_id parameter binding required")
