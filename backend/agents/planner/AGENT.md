# Planner Agent — TF-E3 Part 1

## Responsibility

- Convert a user NL request into structured task drafts and summaries
- Apply regex-based input security scanning before any LLM call
- Validate and parse JSON output into Pydantic models

## Verification Gate

Run backend verification:

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

