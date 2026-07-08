# Context Agent — TF-E3 Part 1

## Responsibility

- Fetch task/project/comment context via MCP (read-only)
- Apply spotlighting to all external text content
- Sort and truncate results for planner input

## Verification Gate

Backend verification:

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

