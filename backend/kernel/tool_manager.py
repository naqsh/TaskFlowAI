from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from typing import Any, Protocol

from backend.kernel.errors import (
    MCPTimeoutError,
    MCPValidationError,
    ToolChainLimitExceeded,
    ToolNotAllowedError,
)


class MCPClientProtocol(Protocol):
    async def call_tool(self, tool: str, params: dict[str, Any]) -> Any: ...


class MCPResponseValidatorProtocol(Protocol):
    def validate(self, tool: str, response: Any) -> Any: ...


class ToolManager:
    """Tool sandbox enforcement for MCP tool calls (Part 1 scaffold)."""

    def __init__(
        self,
        mcp_client: MCPClientProtocol,
        *,
        validator: MCPResponseValidatorProtocol | None = None,
        allowlist: dict[str, list[str]] | None = None,
        max_chain_calls: int = 3,
        timeout_seconds: float = 30.0,
        tool_allowlist_path: str | None = None,
    ) -> None:
        self._mcp_client = mcp_client
        self._validator = validator
        self._max_chain_calls = max_chain_calls
        self._timeout_seconds = timeout_seconds
        self._tool_call_counts: dict[str, int] = {}

        self._allowlist: dict[str, list[str]] = allowlist or self._load_allowlist(
            tool_allowlist_path
        )

    @staticmethod
    def _default_allowlist() -> dict[str, list[str]]:
        return {
            "context_agent": ["tasks.list", "projects.list", "comments.list"],
            "planner_agent": [],
        }

    def _load_allowlist(self, tool_allowlist_path: str | None) -> dict[str, list[str]]:
        if tool_allowlist_path:
            try:
                with open(tool_allowlist_path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    return {
                        str(k): [str(x) for x in v] for k, v in raw.items() if isinstance(v, list)
                    }
            except FileNotFoundError:
                pass
        # Optional default location.
        candidate = tool_allowlist_path
        if candidate is None:
            candidate = os.path.join(os.getcwd(), "tool_allowlist.json")
        try:
            if os.path.exists(candidate):
                with open(candidate, encoding="utf-8") as f:
                    raw2 = json.load(f)
                if isinstance(raw2, dict):
                    return {
                        str(k): [str(x) for x in v] for k, v in raw2.items() if isinstance(v, list)
                    }
        except Exception:
            pass

        return self._default_allowlist()

    def reset_tool_call_counts(self) -> None:
        self._tool_call_counts = {}

    async def execute_tool(self, agent_id: str, tool: str, params: Mapping[str, Any]) -> Any:
        """Execute a single MCP tool call with allowlist + chain + timeout checks."""

        allowed_tools = self._allowlist.get(agent_id, [])
        if tool not in allowed_tools:
            raise ToolNotAllowedError(f"tool_not_allowed agent_id={agent_id} tool={tool}")

        current = self._tool_call_counts.get(agent_id, 0)
        if current >= self._max_chain_calls:
            raise ToolChainLimitExceeded(
                "tool_chain_limit_exceeded "
                f"agent_id={agent_id} tool={tool} "
                f"max_calls={self._max_chain_calls}"
            )
        self._tool_call_counts[agent_id] = current + 1

        try:
            raw_response = await asyncio.wait_for(
                self._mcp_client.call_tool(tool=tool, params=dict(params)),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as e:
            raise MCPTimeoutError(f"mcp_timeout tool={tool} agent_id={agent_id}") from e

        if self._validator is None:
            return raw_response

        try:
            return self._validator.validate(tool=tool, response=raw_response)
        except Exception as e:  # noqa: BLE001 - validation errors are wrapped
            raise MCPValidationError(
                f"mcp_validation_failed tool={tool} agent_id={agent_id}"
            ) from e
