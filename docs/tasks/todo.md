# TaskFlow AI — Active Task Plan

**Epic:** TF-E3 — MVP 3: AI Intelligence (Part 2)
**Branch:** `epic/TF-E3-ai-intelligence-part2`
**Status:** TF-031..TF-040 complete (hardened + tested)

---

## Session plan (YOLO — TF-E3 Part 2)

1. Audit existing Part 2 scaffold vs `TF-E3-ai-intelligence-part2.json` tickets
2. Harden consensus, adversarial, orchestrator present schema, prompt loader, AI headers, FE preview
3. Add backend unit tests for TF-031..039 criteria + FE Vitest for consent/badge
4. Run verification gates; sync `todo.md`, `lessons.md`, `PLAN.md`, `OBSERVABILITY.md`

---

## Completed (TF-009)

- [x] TF-009 — Comments API and XSS sanitization

---

## Completed (TF-008)

- [x] TF-008 — Projects and Tasks CRUD API

---

## Completed (TF-010)

- [x] TF-010 — Dashboard and task management frontend

---

## Completed (TF-011)

- [x] TF-011 — Audit logs + OpenTelemetry baseline

---

## Verification Commands

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
cd frontend && npm run test && npm run lint && npm run build
```

---

## Completed (TF-E2)
**Epic:** TF-E2 — MVP 2: Collaboration  
**Branch:** `epic/TF-E2-collaboration`

### Implemented
- [x] TF-013 — In-App Notifications
- [x] TF-014 — File Attachments
- [x] TF-015 — Search and Filters API
- [x] TF-016 — Activity Timeline API
- [x] TF-017 — Transactional Email
- [x] TF-018 — Redis Caching and Rate Limiting
- [x] TF-019 — Frontend integration
- [x] TF-020 — Integration tests + docs sync

---

## Completed (TF-E3)
**Epic:** TF-E3 — MVP 3: AI Intelligence (Part 1)
**Branch:** `epic/TF-E3-ai-intelligence`

### Implemented
- [x] TF-021 — AgentResultEnvelope and LangGraph State
- [x] TF-022 — Agent OS Kernel Scaffold
- [x] TF-023 — PostgreSQL MCP Client (stdio)
- [x] TF-024 — Context Agent Implementation
- [x] TF-025 — LLM Router with Model Fallback
- [x] TF-026 — Planner Agent Implementation
- [x] TF-027 — Spotlighting Utility and Integration
- [x] TF-028 — InputSecurityScanner Scaffold
- [x] TF-029 — CoALA Memory Foundation
- [x] TF-030 — Tool Manager MCP Sandbox Hardening

**TF-E3 Part 1 proof:** backend verification gate passed (see earlier session notes).

---

## Completed (TF-E3 Part 2)
**Epic:** TF-E3 — MVP 3: AI Intelligence (Part 2)
**Branch:** `epic/TF-E3-ai-intelligence-part2`

### Implemented
- [x] TF-031 — Verification Agent Implementation
  - `backend/agents/verification/node.py`, `AGENT.md`
  - Schema/priority/due_date + summary-mode edge cases
- [x] TF-032 — Adversarial Agent Implementation
  - Overdue / workload / summary hallucination checks; top-3 concerns
- [x] TF-033 — Critic Agent (Safety Gatekeeper)
  - `InputSecurityScanner` on planner+context; no retry on security
- [x] TF-034 — Consensus Evaluator
  - `backend/graph/consensus.py` — security > verification > adversarial > mcp_timeout
- [x] TF-035 — Orchestrator Agent (Supervisor + Presenter)
  - route / present / escalation; nh3 sanitize; stable AIResponse keys
- [x] TF-036 — Full AI graph wiring
  - `backend/graph/builder.py` ainvoke pipeline + 1 retry + circuit breaker
- [x] TF-037 — AI API Endpoints
  - `POST /api/v1/ai/parse-task|summarize|prioritize`, `X-Trace-Id`, 10/min AI rate limit
- [x] TF-038 — Prompt Packs v2.0.0 (11-file + CONTRACT)
  - `prompts/{agent}/*` (6 agents × 12 files), `backend/llm/prompt_loader.py`
- [x] TF-039 — Prompt caching and token metrics
  - `LLMRouter.build_cached_system_messages`, Prometheus gauges, `docs/OBSERVABILITY.md`
- [x] TF-040 — AI Frontend — Consent Modal and AI Features UI
  - `AITaskCreator` preview-before-save, consent modal, ObservabilityBadge, AIProjectSummary

---
**TF-E3 Part 2 proof (2026-07-08):**
- `uv run ruff check backend` ✅
- `uv run mypy backend` ✅ (140 source files)
- `uv run pytest` ✅ **115 passed, 26 skipped** (incl. `test_tf_e3_part2_agents.py` 22 cases)
- `cd frontend && npm test` ✅ **5 passed** (CommentThread + AIComponents)

---
*Updated: July 2026 — TF-E3 Part 2 complete (hardened)*
