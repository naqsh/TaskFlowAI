# TaskFlow AI — Active Task Plan

**Epic:** TF-E1 — MVP 1 Foundation  
**Branch:** `epic/TF-E1-foundation`  
**Status:** TF-008 complete — TF-009 next

---

## Completed (TF-008)

- [x] TF-008 — Projects and Tasks CRUD API
  - `backend/api/v1/projects.py`, `backend/api/v1/tasks.py`
  - `backend/services/project_service.py`, `backend/services/task_service.py`
  - `backend/repositories/project_repository.py`, extended `task_repository.py`
  - `backend/schemas/project.py`, `backend/schemas/task.py`
  - `backend/security/sanitization.py` — nh3 on descriptions
  - `backend/tests/test_projects_tasks.py`, `backend/tests/test_sanitization.py`
  - RBAC via `require_permission` (projects) and `WorkspaceAuthContext` + ABAC (tasks)

---

## Completed (TF-007)

- [x] TF-007 — RBAC/ABAC enforcement

---

## Completed (TF-006)

- [x] TF-006 — JWT auth + login/register UI

---

## Next Up

- [ ] TF-009 — Comments + XSS sanitization
- [ ] TF-010 — Dashboard UI
- [ ] TF-011 — Audit logs + OpenTelemetry baseline

---

## Verification Commands

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

**TF-008 proof:** 49 passed, 15 skipped (integration).

---

*Updated: July 2026 — TF-008 complete*
