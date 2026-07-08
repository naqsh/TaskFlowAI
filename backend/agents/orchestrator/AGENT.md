# Orchestrator Agent (TF-035)

Role: Route and present structured AI output to the API layer.

MVP for Part 2:
- `orchestrator_present_node`: sanitize string fields and build a JSON response.
- `orchestrator_handle_escalation_node`: return degraded/failure JSON without leaking internals.

Sub-agents are never allowed to output user-facing content; only the orchestrator composes the final payload.
