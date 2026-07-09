# Identity Propagation — TaskFlow AI (TF-049)

## Overview

DelegationContext propagates user intent from API → LangGraph → MCP tool calls, preventing confused deputy attacks where agents act outside their authorized scope.

## DelegationContext Fields

| Field | Description |
|---|---|
| `user_id` | Authenticated user UUID from JWT |
| `session_id` | Composite `{user_id}:{workspace_id}` |
| `agent_id` | Agent requesting MCP access |
| `intent` | Scoped intent: `read_tasks`, `read_projects`, etc. |
| `permissions` | Derived permission list from intent |
| `issued_at` | UTC issuance timestamp |
| `expires_at` | UTC expiry (TTL ≤ 900s) |
| `parent_trace_id` | Request trace ID for audit correlation |

## Flow

```
JWT → API handler → IdentityManager.create_delegation_context()
  → TaskFlowGraphState.delegation_context
  → ToolManager.execute_tool(delegation=...)
  → CredentialBroker.get_credential() → access_token in MCP params
  → validate_delegation(tool=...) → MCP call
```

## Confused Deputy Prevention

- Agents never use their own credentials; JIT tokens issued via CredentialBroker
- `intent` must match MCP tool (`tasks.list` → `read_tasks`)
- `agent_id` in delegation must match calling agent
- Expired or revoked sessions reject immediately

## Configuration

| Setting | Default | Description |
|---|---|---|
| `DELEGATION_GRACE_SECONDS` | 30 | Clock skew grace window |

## Files

- `backend/security/delegation.py` — core dataclass and validation
- `backend/kernel/identity_manager.py` — issuance and session revocation
- `backend/kernel/tool_manager.py` — MCP enforcement gate
