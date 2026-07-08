# TaskFlow AI — Active Task Plan

**Epic:** TF-E1 — MVP 1 Foundation  
**Branch:** `task/TF-009-comments-api`  
**Status:** TF-009 complete — TF-010 next

---

## Completed (TF-009)

- [x] TF-009 — Comments API and XSS sanitization
  - `backend/api/v1/comments.py`, `backend/services/comment_service.py`
  - `backend/repositories/comment_repository.py`, `backend/schemas/comment.py`
  - `backend/security/sanitization.py` — `sanitize_comment_body` (p, br, strong, em, code)
  - `frontend/components/CommentThread.tsx` — DOMPurify before render
  - `frontend/lib/comments.ts`, `frontend/__tests__/CommentThread.test.tsx`
  - 15-minute author edit window; 409 on archived tasks; manager delete via ABAC

---

## Completed (TF-008)

- [x] TF-008 — Projects and Tasks CRUD API

---

## Next Up

- [ ] TF-010 — Dashboard UI
- [ ] TF-011 — Audit logs + OpenTelemetry baseline

---

## Verification Commands

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
cd frontend && npm run test && npm run lint && npm run build
```

**TF-009 proof:** 54 passed, 20 skipped (backend); 2 passed (frontend Vitest).

---

*Updated: July 2026 — TF-009 complete*
