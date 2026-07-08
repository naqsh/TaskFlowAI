from __future__ import annotations

from uuid import uuid4

import pytest

from backend.mcp.postgres_stdio import PostgresMCPClient


@pytest.mark.asyncio
async def test_postgres_mcp_rejects_unknown_tool() -> None:
    client = PostgresMCPClient()
    with pytest.raises(ValueError):
        await client.call_tool("unknown.tool", {"user_id": uuid4(), "workspace_id": uuid4()})


@pytest.mark.asyncio
async def test_postgres_mcp_requires_user_id_param() -> None:
    client = PostgresMCPClient()
    with pytest.raises(ValueError):
        await client.call_tool("tasks.list", {"workspace_id": uuid4()})


@pytest.mark.asyncio
async def test_postgres_mcp_rejects_unparameterized_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure we stay on mock mode; stdio isn't executed in unit tests.
    monkeypatch.setenv("MCP_TRANSPORT", "mock")
    client = PostgresMCPClient()

    with pytest.raises(ValueError):
        await client.call_tool(
            "tasks.list",
            {
                "user_id": uuid4(),
                "workspace_id": uuid4(),
                "sql": "SELECT * FROM tasks WHERE workspace_id = $2",
            },
        )

    # Allowed when it includes parameter binding hints.
    await client.call_tool(
        "tasks.list",
        {
            "user_id": uuid4(),
            "workspace_id": uuid4(),
            "sql": "SELECT * FROM tasks WHERE user_id = :user_id",
        },
    )
