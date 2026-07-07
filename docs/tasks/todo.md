# TaskFlow AI — Active Task Plan

**Epic:** TF-E1 — MVP 1 Foundation  
**Branch:** `epic/TF-E1-foundation` (from `epic/taskflow-implementation`)  
**Ticket file:** `docs/jira-tickets-json/TF-E1-mvp1-foundation.json`  
**Status:** TF-006 complete — TF-007 next

---

## Completed (TF-006)

- [x] TF-006 — JWT auth + login/register UI
  - `backend/api/v1/auth.py` — register, login, refresh, logout, me
  - `backend/services/auth_service.py` — bcrypt, JWT, refresh rotation
  - `backend/schemas/auth.py`, `dependencies/auth.py`, `dependencies/database.py`
  - `backend/repositories/user_repository.py`, `refresh_token_repository.py`
  - `backend/security/rate_limit.py` — login 10/min per IP
  - `alembic/versions/002_refresh_tokens.py`
  - `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`
  - `frontend/lib/auth.ts` — token storage
  - `backend/tests/test_auth.py` — unit + integration (TEST_DATABASE_URL)

---

## Completed (Scaffold)

- [x] TF-001 — Monorepo init
- [x] TF-002 — Docs scaffold
- [x] TF-003 — FastAPI backend scaffold
- [x] TF-004 — Next.js frontend scaffold
- [x] TF-012 — CI pipeline + Docker backend

---

## Completed (TF-005)

- [x] TF-005 — Supabase async SQLAlchemy + Alembic + RLS schema

---

## Next Up

- [ ] TF-007 — RBAC/ABAC
- [ ] TF-008 — Projects and Tasks CRUD
- [ ] TF-009 — Comments + XSS sanitization
- [ ] TF-010 — Dashboard UI
- [ ] TF-011 — Audit logs + OpenTelemetry baseline

---

## Verification Commands

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
cd frontend && npm run lint && npm run build
```

**TF-006 proof:** 24 passed, 7 skipped (integration); frontend build OK.

---

*Updated: July 2026 — TF-006 complete*
