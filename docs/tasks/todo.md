# TaskFlow AI — Active Task Plan

**Epic:** TF-E1 — MVP 1 Foundation  
**Branch:** `task/TF-010-dashboard-ui`  
**Status:** TF-010 complete — TF-011 next

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

## Completed (TF-010)

- [x] TF-010 — Dashboard and task management frontend
  - Auth-gated homepage (`frontend/app/page.tsx`, `frontend/components/RootPage.tsx`)
  - React Query provider (`frontend/components/QueryProvider.ts`, `frontend/app/layout.tsx`)
  - Project/task UI: `frontend/components/Dashboard.tsx`, `frontend/components/ProjectCard.tsx`, `frontend/components/TaskList.tsx`, `frontend/components/TaskForm.tsx`
  - Pages: `frontend/app/projects/[id]/page.tsx`, `frontend/app/tasks/[id]/page.tsx`
  - Comment rendering wired via `CommentThread` + `useComments` optimistic hook
  - UI primitives: `frontend/components/ui/*`

---

## Next Up

- [ ] TF-011 — Audit logs + OpenTelemetry baseline

---

## Verification Commands

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
cd frontend && npm run test && npm run lint && npm run build
```

**TF-010 proof:** `npm run test` passed; `npm run lint` passed (warnings allowed); `npm run build` succeeded.

---

*Updated: July 2026 — TF-010 complete*
