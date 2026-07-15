# Refactoring Agents — TaskFlow AI (ADR-004)

**Version:** 0.1.0 | **Last Updated:** 2026-07-16

## Scope

Agentic code-refactoring loop stages implemented as envelope-returning nodes:

| Node | Role | Stage |
|---|---|---|
| `search_agent_node` | `tool_operator` | Search (AST symbol/call-site scan) |
| `report_agent_node` | `planner` | Report (prioritized findings) |
| `patch_agent_node` | `tool_operator` | Patch (deterministic AST rename) |
| `verify_agent_node` | `verifier` | Verify (parse + optional command) |

Orchestration and human-approval gating live in `backend/refactoring/service.py`.

## Safety

- Never patch without approved finding IDs
- Snapshot before patch; rollback on verify failure
- Paths confined to `REFACTORING_SANDBOX_ROOT`
- Feedback JSONL records accept/reject + verify outcomes

## References

- [docs/adr/ADR-004-ai-code-refactoring-alignment.md](../../../docs/adr/ADR-004-ai-code-refactoring-alignment.md)
