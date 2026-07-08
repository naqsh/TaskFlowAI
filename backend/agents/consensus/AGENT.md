# Consensus Evaluator (TF-034)

Role: Deterministic aggregator of results from Verification, Adversarial, and Critic.
Pure Python — no LLM call.

## Rules (priority order)

1. Missing agent result ⇒ `escalation` / `mcp_timeout` / `retry_allowed=false`
2. Critic `security_violation_detected` ⇒ `rejected` / `retry_allowed=false`
3. Verification `verification_failed` ⇒ `escalation` / `retry_allowed=true` (max 1)
4. Adversarial `adversarial_concerns` ⇒ `escalation` / `retry_allowed=true` (regenerate)
5. Otherwise ⇒ `agreement`

Major severity always wins over minor when merging concerns upstream.
Summary-only mode uses the same consensus rules with different field checks in agents.

