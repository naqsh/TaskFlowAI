# Graph Types — TaskFlow AI

## Scope

Governs `backend/graph/` types used by LangGraph multi-agent workflows.

## Inputs / Outputs

- `TaskFlowGraphState` is the typed routing state shared between agent nodes.
- Agent nodes write partial results into `context_result`, `planner_result`, etc.

## Security Constraints

- Never place credentials/secrets in graph state.
- Treat all external content as untrusted; pass it through spotlighting before LLM use.

## Verification Gate

- Run: `uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest`

