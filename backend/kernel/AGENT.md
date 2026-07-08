# Agent OS Kernel — TF-E3 Part 1

## Scope

Governs kernel scaffolds introduced in TF-E3 Part 1:

- `AgentScheduler` — establish execution ordering (context before planner)
- `MemoryManager` — working + episodic foundation stubs
- `ToolManager` — MCP sandbox enforcement (allowlists, tool-chain limit, timeouts)
- `IdentityManager` — delegation context stub
- `SecurityMonitor` — execution metrics recording

## Verification Gate

Run before marking backend tasks done:

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

