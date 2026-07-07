# JIRA Tickets JSON Directory — TaskFlow AI

**Version:** 2.0.0 | **Last Updated:** July 2026

---

## Purpose

This directory contains JSON exports of epics and tasks that drive the TaskFlow AI implementation backlog. Cursor Development Agents use the structured data here to perform step-by-step implementation with full context of requirements, acceptance criteria, and dependencies.

**Source of truth:** `docs/TaskFlowAI_Project_Proposal.md` v2.0.0

---

## Directory Structure

```
docs/jira-tickets-json/
├── README.md                              # This file
├── TF-E1-mvp1-foundation.json             # MVP 1: Foundation (12 tasks)
├── TF-E2-mvp2-collaboration.json          # MVP 2: Collaboration (8 tasks)
├── TF-E3-ai-intelligence-part1.json     # MVP 3: AI — kernel, MCP, context, planner (10 tasks)
├── TF-E3-ai-intelligence-part2.json     # MVP 3: AI — verification, graph, prompts, UI (10 tasks)
├── TF-E4-security-layer1.json             # MVP 4: Security hardening (8 tasks)
├── TF-E5-identity-credentials.json        # MVP 5: Identity & JIT credentials (6 tasks)
├── TF-E6-production.json                  # MVP 6: Production & supply chain (8 tasks)
└── TF-E7-hybrid-deploy.json               # Option A: Vercel FE + Docker BE (6 tasks)
```

**Total: 68 tasks across 7 epics**

**Integration branch:** `epic/taskflow-implementation`

---

## Canonical Task Format

All epic and task JSON files use the flat-array format with a rich `Description` column. Reference: `TF-E1-mvp1-foundation.json`.

```json
{
  "TF-E1": [
    {
      "Issue id": "TF-E1",
      "Summary": "MVP 1: Foundation",
      "Issue Type": "Epic",
      "Description": "Epic scope...\n\nSCOPE:\n...\n\nSUCCESS CRITERIA:\n...",
      "Labels": "mvp1,foundation",
      "Parent": ""
    },
    {
      "Issue id": "TF-001",
      "Summary": "Monorepo Init",
      "Issue Type": "Task",
      "Description": "One-line summary.\n\nUSE CASES:\n- User story scenarios\n\nIMPLEMENTATION DETAILS:\n- Files and changes\n\nEFFORT: M (4 hours)\nPROJECT AREA: Backend\nDEPENDENCIES: None\n\nTESTING CRITERIA:\n- Pass conditions\n\nEDGE CASES:\n- Failure modes",
      "Labels": "scaffold,mvp1",
      "Parent": "TF-E1"
    }
  ]
}
```

### Description Field Sections (Required per Task)

| Section | Required | Purpose |
|---|---|---|
| Summary line | Yes | One-sentence task goal before sections |
| `USE CASES` | Yes | User scenarios and acceptance flows |
| `IMPLEMENTATION DETAILS` | Yes | Files to create/modify, APIs, config |
| `EFFORT` | Yes | T-shirt size and hours (e.g. `M (4 hours)`) |
| `PROJECT AREA` | Yes | Backend, Frontend, CI/CD, Docs, etc. |
| `DEPENDENCIES` | Yes | Prior task IDs or epic prerequisites |
| `TESTING CRITERIA` | Yes | Tests and measurable acceptance checks |
| `EDGE CASES` | Yes | Fail-safe behaviour — **Coding Agent must implement all** |

Epic entries (`Issue Type: Epic`) use `SCOPE`, `REFERENCE DOCS`, and `SUCCESS CRITERIA` instead of implementation sections.

---

## Backend Verification Gate (Required Before Task Complete)

```bash
uv run ruff check backend && uv run ruff format backend && uv run mypy backend && uv run pytest
```

See `backend/AGENT.md` and root `AGENT.md` workflow rules.

---

## Workflow Rules

| Rule | Behaviour |
|---|---|
| JSON Sync | When JSON files change, update `docs/PLAN.md` |
| Edge Cases | Coding Agent MUST implement all `EDGE CASES` in Description |
| Dependencies | Check prerequisite tasks before starting |
| Epic branch | `epic/TF-E{n}-{name}` from `epic/taskflow-implementation` |

---

*TaskFlow AI JIRA Tickets JSON — Version 2.0.0 — July 2026*
