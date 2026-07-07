# FINAL EXECUTION RULES — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

Source of truth for execution standards and workflow discipline. Applies to all Cursor Development Agents on this project.

---

## 1. Production-Ready Code Requirements

- **No pseudo-code** — fully functioning implementations only
- **No fabricated metrics** — wire telemetry to OpenTelemetry/Prometheus, not hardcoded values
- **No untyped APIs** — Pydantic v2 (backend) and Zod/TypeScript (frontend)
- **No hardcoded secrets** — inject via environment variables, validated by pydantic-settings
- **Clean Architecture** — API → Service → Repository; no SQL in route handlers

---

## 2. Workflow Execution Rules

### MUST Do

1. **Plan mode** for tasks with 3+ steps or architectural decisions
2. **Task logging** — write plan to `docs/tasks/todo.md` before coding
3. **Verification gate** — backend tasks must pass:

   ```bash
   uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
   ```

4. **Lessons review** — read `docs/tasks/lessons.md` at session start
5. **Correction loop** — update `lessons.md` after user corrections
6. **Done gate** — prove completion with tests, logs, or diffs
7. **Edge cases** — implement all `EDGE CASES` from JSON ticket descriptions
8. **Token efficiency** — follow `docs/TOKEN-EFFICIENCY.md` before `docs/KICKOFF-PROMPT.md`

### MUST NOT Do

- Implement before plan confirmed
- Mark done without evidence
- Edit out-of-scope files
- Re-read `KICKOFF-PROMPT.md` on continuation sessions

---

## 3. Agent Rules (MVP 3+)

- All LangGraph nodes return `AgentResultEnvelope`
- Only Orchestrator/API produces user-facing content
- Failed agents route to DLQ
- External user content uses spotlighting before LLM calls

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind 4, shadcn/ui, TanStack Query |
| Backend | FastAPI, uv, Pydantic v2, SQLAlchemy async, Alembic |
| Database | Supabase PostgreSQL with RLS |
| Deploy | Vercel (FE) + Docker/GHCR (BE) |
| CI | GitHub Actions — ruff, mypy, pytest, eslint, docker build |

---

## 5. Testing

- Backend: pytest-asyncio, >80% coverage target
- Frontend: Vitest, >75% coverage target
- Security tests added in MVP 4

---

## 6. Documentation Sync

| Trigger | Action |
|---|---|
| JSON ticket changed | Update `docs/PLAN.md` |
| Task completed | Update `docs/tasks/todo.md` |
| User correction | Update `docs/tasks/lessons.md` |
| New agent folder | Create co-located `AGENT.md` |

---

## 7. Context Management

At ~75% context usage, write `docs/tasks/checkpoint.md` with epic, branch, current task, files touched, and next steps. Commit WIP.

---

## 8. Git Branch Policy

| Branch | Purpose |
|---|---|
| `epic/taskflow-implementation` | Long-lived integration branch |
| `epic/TF-E{n}-{name}` | Per-epic work branch |

Merge epics with **merge commit** (not squash). Delete local epic branch after merge; keep remote.

---

*TaskFlow AI Execution Rules — Version 0.1.0*
