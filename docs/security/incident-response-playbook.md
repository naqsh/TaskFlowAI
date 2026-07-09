# Incident Response Playbook — TaskFlow AI (TF-061)

**Version:** 1.0.0 | **Last Updated:** July 2026  
**SLA:** Security dwell time P95 < 3600s (1 hour)

## 1. Prompt injection spike

**Detection:** DLQ `security_violation_detected` rate ↑; `InputSecurityScanner` block rate >10%

**Response (target: 15 min):**

1. Confirm spike in Grafana / DLQ admin API
2. Set `AI_FEATURES_ENABLED=false` if block rate >25%
3. Export DLQ samples for forensic review
4. Check for new jailbreak patterns — update `jailbreak_corpus.yaml` if needed
5. Re-enable AI after corpus/rules update and smoke tests pass

## 2. DLQ flood

**Detection:** `dlq_events` insert rate >100/min

**Response:**

1. Rate-limit `/api/v1/ai/*` (already 10 req/min per IP)
2. Identify offending workspace/session from audit logs
3. Suspend workspace AI consent if malicious
4. Scale backend replicas if capacity-related

## 3. Credential compromise

**Detection:** Anomalous MCP tool calls; vault audit anomalies

**Response:**

1. Rotate `JWT_SECRET_KEY` (forces re-auth)
2. Revoke active delegation tokens via identity manager
3. Disable MCP: stop MCP server processes / block egress
4. Rotate third-party API keys in vault
5. Post-incident vendor notification per [GOVERNANCE.md](../GOVERNANCE.md)

## 4. MCP / tool poisoning

**Detection:** `quarantined_mcp_responses` growth; anomaly σ alerts

**Response:**

1. Review quarantined responses in admin tooling
2. Tighten MCP URL allowlist
3. Disable affected tools in `agent-manifest.json` (re-sign + deploy)

## Post-incident template (lessons.md)

```markdown
| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| YYYY-MM-DD | <what went wrong> | <why> | <preventive rule> |
```

## Escalation

| Severity | Contact |
|---|---|
| P1 — active exploitation | On-call + Security lead |
| P2 — elevated block rate | On-call |
| P3 — single incident | Next business day review |

## Related metrics

- `security_dwell_time_seconds`
- `blast_radius_score`
- `prompt_cache_hit_rate`
- DLQ depth by `failure_reason`
