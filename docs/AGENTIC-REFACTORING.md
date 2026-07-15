# Agentic Code Refactoring — TaskFlow AI (ADR-004)

## Overview

Sandboxed, human-gated agentic refactoring loop for mechanical Python changes (starting with symbol rename). Distinct from the task-AI LangGraph pipeline.

## Loop

Goal → Plan → Search → Report → **Human approval** → Snapshot → AST Patch → Verify → Rollback / Feedback

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/refactoring/analyze` | Search + report findings (no mutation) |
| `POST` | `/api/v1/refactoring/apply` | Apply approved finding IDs |
| `POST` | `/api/v1/refactoring/feedback` | Record rejected findings |
| `GET` | `/api/v1/refactoring/runs/{run_id}` | Fetch run report |

Requires: `REFACTORING_ENABLED=true`, `REFACTORING_SANDBOX_ROOT`, workspace **admin**, AI consent.

## Safety

- Path jail under sandbox root
- No patch without approved finding IDs
- Snapshot before mutation; restore on verify failure
- Feedback JSONL for accept/reject and verify outcomes

## Files

- `backend/refactoring/`
- `backend/agents/refactoring/`
- `backend/api/v1/refactoring.py`
- `docs/adr/ADR-004-ai-code-refactoring-alignment.md`
