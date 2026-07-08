from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class StdioTransport:
    """stdio transport stub for MCP Part 1.

    Real spawning of `@modelcontextprotocol/server-postgres` is intentionally
    not executed in unit tests. When used in dev, wire this transport to a
    subprocess and forward `request()` calls over stdio.
    """

    async def request(self, tool: str, params: Mapping[str, Any]) -> Any:  # pragma: no cover
        raise NotImplementedError("StdioTransport is not implemented in MVP Part 1 tests")
