# Token Efficiency Rules — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

Rules for Cursor Development Agents to minimize context window usage. **Read before `docs/KICKOFF-PROMPT.md`.**

---

## 1. What to Read (and Skip)

### Every session

| Read (in order) | Skip unless task requires it |
|---|---|
| `docs/tasks/checkpoint.md` | `docs/KICKOFF-PROMPT.md` |
| `docs/tasks/lessons.md` | `docs/ARCHITECTURE.md` |
| `AGENT.md` | Other epic JSON files |
| `docs/TOKEN-EFFICIENCY.md` | Full `.cursor/rules/*` |
| `docs/PLAN.md` | Domain docs (`SECURITY.md`, etc.) |
| `docs/EXECUTION-RULES.md` | `docs/example-code/` |

### Fresh kickoff only

- `docs/KICKOFF-PROMPT.md`
- Current epic JSON only (e.g. `docs/jira-tickets-json/TF-E1-mvp1-foundation.json`)
- Relevant `.cursor/rules/*.mdc` for active phase

---

## 2. Tool Use

| Do | Don't |
|---|---|
| `Grep` / `Glob` then targeted `Read` | Read entire directories |
| `Read` with offset/limit on large files | Re-read checkpoint-covered files |
| Batch parallel tool calls | Sequential discovery |
| Delegate broad exploration to subagents | Manual repo map file-by-file |

---

## 3. Implementation Discipline

- Minimal diffs — change only what the task requires
- Checkpoint is truth — resume from `checkpoint.md`
- Scope docs on demand — open domain docs only when needed

---

## 4. Context Handoff

Write `docs/tasks/checkpoint.md` at ~75% context. Commit WIP before session end.

---

*Token Efficiency Rules — TaskFlow AI — Version 0.1.0*
