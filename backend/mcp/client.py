from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class MCPTransportProtocol(Protocol):
    async def request(self, tool: str, params: Mapping[str, Any]) -> Any: ...


class MCPClientProtocol(Protocol):
    async def call_tool(self, tool: str, params: dict[str, Any]) -> Any: ...


class MCPClient:
    """Base MCP client abstraction."""

    async def call_tool(self, tool: str, params: dict[str, Any]) -> Any:
        raise NotImplementedError
