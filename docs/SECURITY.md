# TaskFlow AI — Security Framework (MVP 4)

**Version:** 1.0.0 | **Last Updated:** July 2026

## Defense in Depth

| Layer | Component | Role |
|---|---|---|
| Input | `InputSecurityScanner` | regex → PromptGuard 2 → constitutional |
| Context | Spotlighting | `<<<EXTERNAL_CONTENT>>>` data-only markers |
| Tool | `MCPResponseValidator` | schema → sanitization (nh3) → anomaly detection |
| Failure | DLQ | Persist security violations and failed runs |
| Integrity | `AuditLogWriter` | Hash-chain sealed audit entries |
| Observability | `SecurityMonitor` | Dwell time, blast radius, MCP baselines |

## Input Security Scanner

Pipeline in `backend/security/input_scanner.py`:

1. **Regex** — `PromptInjectionDetector` (NFKC, base64/hex decode)
2. **ML** — `PromptGuardService` (LlamaFirewall PromptGuard 2 when `HF_TOKEN` set)
3. **Constitutional** — `ConstitutionalClassifier` loads `backend/security/rules.yaml`

### Configuration

| Env | Default | Description |
|---|---|---|
| `LLAMAFIREWALL_ENABLED` | `true` | Enable ML layer |
| `LLAMAFIREWALL_BLOCK_THRESHOLD` | `0.9` | ML block threshold |
| `HF_TOKEN` | — | HuggingFace token for model download |

### Violation handling

- Input violations route to DLQ with `security_violation_detected` — **no retry**
- Repeated violations (>3/hour per session) rate-limited
- Layer timeout (5s) fails secure (block)

## Constitutional Rules (TF-047)

Rules defined in `backend/security/rules.yaml` (version `1.0.0`):

- System prompt exfiltration
- DAN / jailbreak persona
- Safety guideline bypass
- Privilege escalation
- PII generation requests
- Embedded `[system]` instructions
- Role override attempts
- Data exfiltration

## MCP Tool Poisoning Defense (TF-042)

`MCPResponseValidator` three layers:

1. **Schema** — Pydantic models per tool (`tasks.list`, `projects.list`, `comments.list`)
2. **Sanitization** — nh3 HTML strip; datetimes normalized to UTC ISO
3. **Anomaly** — 2σ response size deviation; quarantine table `quarantined_mcp_responses`

Internal/private URLs blocked by allowlist.

## Dead Letter Queue (TF-043)

- Table: `dlq_events`
- Admin API: `GET /api/v1/dlq`, `POST /api/v1/dlq/{id}/retry`
- Security violations cannot be retried (403)
- `verification_failed` may retry (max 3)

## Dwell Time SLO (TF-044)

- Metric: `security_dwell_time_seconds{incident_type}`
- Target: P95 < 3600s (1 hour)
- Recorded via `SecurityMonitor.record_incident_start/detected`

## Blast Radius (TF-045)

- Gauge: `blast_radius_score{agent_id}` — target <30 under normal load
- Factors: tool calls, tokens, escalation rate (normalized per request)

## Audit Chain Sealing (TF-046)

- `entry_hash = sha256(prev_hash + canonical_json)`
- Genesis `prev_hash`: 64 zero hex chars
- `verify_audit_chain()` detects tampering
- Payloads >10KB stored as SHA-256 only

## CI Gates

- `jailbreak_corpus.yaml`: >95% block rate (`test_security.py`)
- `legitimate_tasks_corpus.yaml`: <1% false positives
- `test_tool_poisoning.py`: quarantine and sanitization
- `test_security_integration.py`: injection → DLQ → audit chain

## MITRE ATT&CK for AI Systems

Full technique mapping: [security/MITRE-ATTACK-COVERAGE.md](security/MITRE-ATTACK-COVERAGE.md) (TF-057, >80% coverage target).
