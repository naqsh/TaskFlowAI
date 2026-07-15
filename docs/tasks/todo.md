# TaskFlow AI — Active Task Plan

**Epic:** ADR-004 — Agentic Code Refactoring Loop (YOLO)

**Branch:** current working branch

**Status:** ✅ Complete (2026-07-16)

**Cite:** `docs/adr/ADR-004-ai-code-refactoring-alignment.md`

---

## Session plan (ADR-004 YOLO — 2026-07-16)

1. [x] Core `backend/refactoring/` — sandbox, search, snapshot, patch, verify, rollback, feedback, service loop
2. [x] Agent nodes under `backend/agents/refactoring/` returning `AgentResultEnvelope`
3. [x] API `/api/v1/refactoring/*` (analyze → human approve → apply) + feature flag
4. [x] Unit tests for loop stages + AST rename rollback
5. [x] Docs: ADR-004 status update, AGENT.md, proposal, PLAN.md, refactor.mdc, backend AGENT.md
6. [x] Verification gate: ruff, mypy, ADR-004 pytest (`--noconftest` due to host nh3 App Control)

## Safety constraints (must not skip)

- Sandbox-rooted paths only (no traversal outside `REFACTORING_SANDBOX_ROOT`)
- Feature disabled by default (`REFACTORING_ENABLED=false`)
- Human approval of finding IDs required before Patch
- Snapshot before Patch; auto-rollback on verify failure
- Feedback events logged for accepted/rejected + pass/fail

---

## Prior epic

**TF-E6** — ✅ Complete — see PLAN.md
