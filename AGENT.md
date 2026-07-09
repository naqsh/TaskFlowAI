# AGENT.md — TaskFlow AI

## What this file is

Root index for TaskFlow AI. Engineering standards, agent specs, and prompt rules live in co-located `AGENT.md` files alongside the code they govern.

**Architecture:** Clean Architecture | Multi-Agent Orchestration | MCP Servers | Supabase | Hybrid Deploy  
**Deployment:** Vercel Frontend + Docker Backend  
**Version:** 0.1.0 | July 2026

> **Spec:** [docs/TaskFlowAI_Project_Proposal.md](docs/TaskFlowAI_Project_Proposal.md) v2.0.0  
> **Integration branch:** `epic/taskflow-implementation`

---

## Workflow Rules (read at every session start)

| Rule | Behaviour |
|---|---|
| Token usage | Follow `docs/TOKEN-EFFICIENCY.md` — read before `docs/KICKOFF-PROMPT.md` |
| Plan mode | Required for any epic/task with 3+ steps — check `docs/jira-tickets-json/*.json` |
| Edge cases | Review `Description` in JSON tickets — implement every item under `EDGE CASES` |
| Task log | Write plan to `docs/tasks/todo.md` before any implementation |
| Verify plan | Check in before starting — do not build on an unconfirmed plan |
| Lessons review | Read `docs/tasks/lessons.md` at session start before touching code |
| Correction loop | After any mistake is made or corrected by a user: update `docs/tasks/lessons.md` immediately |
| Done gate | Never mark complete without proving it works (tests, logs, diff) |
| Backend verification gate | Before marking any backend task done: `uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest` |
| Security first | Check `docs/SECURITY.md` before modifying agent inputs/outputs (when created) |
| Agent envelope | All agents MUST return `AgentResultEnvelope` (MVP 3+) |
| Orchestrator-as-Presenter | Only API/Orchestrator produces user-facing content (MVP 3+) |
| JIT consent | Never hardcode credentials |
| Json sync | JSON ticket changes MUST update `docs/PLAN.md` |
| Context checkpoint | At ~75% context, write `docs/tasks/checkpoint.md` and commit WIP |

---

## MVP Delivery Overview

| Milestone | Scope Summary | Status |
|---|---|---|
| **MVP 1** | Auth, RBAC, CRUD, docs scaffold, CI, Docker backend | ✅ Complete |
| **MVP 2** | Collaboration, notifications, activity feed | ✅ Complete |
| **MVP 3** | Multi-agent AI, LangGraph, MCP, Agent OS Kernel | ✅ Complete (Part 1 + Part 2) |
| **MVP 4** | Security Layer 1 — injection defense, DLQ, observability | ✅ Complete |
| **MVP 5** | Identity, JIT credentials, delegation tokens | ✅ Complete |
| **MVP 6** | Production, supply chain, Cosign, governance | ✅ Complete |
| **Option A (TF-E7)** | Vercel FE + Docker BE hybrid deploy hardening | Planned |

---

## Where to look

| Concern | File | MVP |
|---|---|---|
| Full specification | docs/TaskFlowAI_Project_Proposal.md | All |
| Execution discipline | docs/EXECUTION-RULES.md | MVP 1 |
| Epic tasks | docs/jira-tickets-json/TF-E*.json | MVP 1–7 |
| Implementation progress | docs/PLAN.md | MVP 1 |
| Token efficiency | docs/TOKEN-EFFICIENCY.md | MVP 1 |
| Kick-off prompt | docs/KICKOFF-PROMPT.md | MVP 1 |
| Active task plan | docs/tasks/todo.md | MVP 1 |
| Identity propagation | docs/IDENTITY-PROPAGATION.md | MVP 5 |
| Agentic consent | docs/AGENTIC-CONSENT.md | MVP 5 |
| Local LLM fallback | docs/LOCAL-LLM.md | MVP 5 |
| Supply chain / AI-BOM | docs/SUPPLY-CHAIN-SECURITY.md | MVP 6 |
| Deployment gates | docs/DEPLOYMENT-GATES.md | MVP 6 |
| Governance | docs/GOVERNANCE.md | MVP 6 |
| Self-improvement log | docs/tasks/lessons.md | MVP 1 |
| Local / Docker setup | docs/guidance/try-it-locally.md | MVP 1 |
| Supabase setup | docs/guidance/supabase-setup.md | MVP 1 |
| Frontend rules | frontend/AGENT.md | MVP 1 |
| Backend rules | backend/AGENT.md | MVP 1 |
| CI/CD & Docker | infrastructure/AGENT.md | MVP 1 |

Per-agent `AGENT.md` files under `backend/agents/` are created during MVP 3 — see `backend/AGENT.md`.

---

## Cursor Development Agents

| Cursor Agent | Scope | Rules File | Order |
|---|---|---|---|
| **Coding Agent** | Endpoints, services, UI components | `.cursor/rules/coding.mdc` | 1st |
| **Refactor Agent** | Schema validation, sanitization | `.cursor/rules/refactor.mdc` | 2nd |
| **Testing Agent** | Boundary and integration tests | `.cursor/rules/testing.mdc` | 3rd |
| **Documentation Agent** | Domain `AGENT.md` and docs sync | `.cursor/rules/docs.mdc` | 4th |

Epic workflow: branch from `epic/taskflow-implementation` → implement → refactor → test → docs → PR → merge commit.

**mTLS extension (MVP 6+):** NHI registry in `backend/security/nhi_registry.py` supports future mTLS by swapping self-signed dev certs for Vault PKI-issued certificates without changing `ToolManager` validation interface.

---

*TaskFlow AI — Version 0.1.0 — July 2026*
