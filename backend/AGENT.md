# Backend AGENT.md — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

---

## Scope

Governs FastAPI backend development: REST endpoints, services, repositories, security utilities, and (MVP 3+) LangGraph orchestration.

---

## Technology Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Runtime (uv-managed) |
| FastAPI | 0.115+ | Async API server |
| Pydantic | 2.8+ | Schema validation |
| SQLAlchemy | 2.x | Async ORM |
| Alembic | 1.x | Migrations |
| structlog | 24.4+ | JSON logging with trace_id |
| Redis | 7.x | Cache and sessions |

---

## Architecture (Clean Architecture)

```
backend/
├── AGENT.md
├── main.py                 # FastAPI entry point
├── settings.py             # pydantic-settings
├── logging_config.py
├── exceptions.py           # AppException hierarchy
├── telemetry.py
├── metrics.py
├── api/v1/                 # Route handlers (thin)
├── services/               # Business logic
├── repositories/           # Data access (async SQLAlchemy)
├── schemas/                # Pydantic request/response models
├── db/                     # Models, session, migrations
├── security/               # Spotlighting, RBAC, injection (MVP 3+)
├── agents/                 # Multi-agent nodes (MVP 3+)
├── graph/                  # LangGraph (MVP 3+)
├── refactoring/            # Agentic code refactoring loop (ADR-004)
└── tests/
```

**Rule:** API → Service → Repository. No SQL in route handlers or services.

---

## Verification Gate

Run before marking any backend task complete:

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

---

## Error Handling

- Use `AppException` subclasses (`NotFoundError`, `ValidationError`, etc.)
- Global handler in `main.py` returns structured JSON errors
- Never catch bare `Exception` in business logic

---

## Logging

- All logs via `structlog` with `trace_id` in context
- `X-Trace-Id` response header set by middleware
- Health endpoint requires no authentication

---

## Security Baseline

- Sanitize HTML with `nh3` in service layer (task/comment descriptions)
- `spotlight_external_content()` in `backend/security/spotlighting.py` for LLM-bound user content
- Propagate `user_id` and `workspace_id` through all data paths (RLS + ABAC)

---

## Links

- Parent: [../AGENT.md](../AGENT.md)
- Spec: [../docs/TaskFlowAI_Project_Proposal.md](../docs/TaskFlowAI_Project_Proposal.md)
- Execution: [../docs/EXECUTION-RULES.md](../docs/EXECUTION-RULES.md)

---

*Backend AGENT.md — TaskFlow AI — Version 0.1.0*
