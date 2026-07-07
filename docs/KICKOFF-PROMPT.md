# Kick-off Prompt — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

Ready-to-use prompt for autonomous implementation sessions.

---

## Pre-Flight Checklist

- [ ] Root `AGENT.md` and `docs/EXECUTION-RULES.md` exist
- [ ] `docs/jira-tickets-json/` contains TF-E1 through TF-E7
- [ ] `docs/tasks/todo.md`, `lessons.md`, `checkpoint.md` exist
- [ ] `.cursor/rules/` contains coding, testing, refactor, docs stubs
- [ ] Git repository initialized on `epic/taskflow-implementation`

---

## Kick-off Prompt (Copy This)

```
You are implementing TaskFlow AI from the scaffolded monorepo.

## Read First (In Order)
1. AGENT.md
2. docs/TOKEN-EFFICIENCY.md
3. docs/EXECUTION-RULES.md
4. docs/tasks/checkpoint.md
5. docs/PLAN.md

## Project Overview
- Enterprise task management with phased multi-agent AI
- Hybrid deploy: Vercel frontend + Docker backend
- Supabase PostgreSQL with RLS
- Clean Architecture: API → Service → Repository

## Mission
Implement the current epic from docs/jira-tickets-json/ following autonomous workflow:

1. Branch from epic/taskflow-implementation
2. Read epic JSON — implement IMPLEMENTATION DETAILS and all EDGE CASES
3. Write plan to docs/tasks/todo.md before coding
4. Backend verification gate before marking backend tasks done
5. Update docs/PLAN.md on completion

## Backend Verification Gate
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest

## Start
Continue TF-E1 from docs/jira-tickets-json/TF-E1-mvp1-foundation.json
```

---

*Kick-off Prompt — TaskFlow AI — Version 0.1.0*
