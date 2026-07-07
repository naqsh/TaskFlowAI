# TaskFlow AI — Active Task Plan

**Epic:** TF-E1 — MVP 1 Foundation  
**Branch:** `epic/TF-E1-foundation`  
**Status:** TF-007 complete — TF-008 next

---

## Completed (TF-007)

- [x] TF-007 — RBAC/ABAC enforcement
  - `backend/security/abac.py` — permission matrix + `check_permission`
  - `backend/dependencies/rbac.py` — `WorkspaceAuthContext`, `require_role`, `require_permission`
  - `backend/repositories/workspace_member_repository.py`
  - `backend/api/v1/workspaces.py` — `GET /workspaces/current` smoke route
  - `backend/tests/test_rbac.py`, `backend/tests/test_idor.py`

---

## Completed (TF-006)

- [x] TF-006 — JWT auth + login/register UI (commit `039f447`)

---

## Next Up

- [ ] TF-008 — Projects and Tasks CRUD
- [ ] TF-009 — Comments + XSS sanitization
- [ ] TF-010 — Dashboard UI
- [ ] TF-011 — Audit logs + OpenTelemetry baseline

---

## Verification Commands

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

**TF-007 proof:** 45 passed, 10 skipped (integration).

---

*Updated: July 2026 — TF-007 complete*
