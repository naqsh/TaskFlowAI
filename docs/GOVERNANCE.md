# Governance — TaskFlow AI (TF-061)

**Version:** 1.0.0 | **Last Updated:** July 2026

## Roles

| Role | Responsibilities |
|---|---|
| Platform Engineering | CI/CD, Docker, deployment gates |
| Security | AI-BOM, MITRE coverage, incident response |
| AI/ML Engineering | Prompt packs, cache warming, agent manifests |
| On-call | Execute playbooks, kill switch, escalation |

## Change management

1. Epic branch from `epic/taskflow-implementation`
2. PR with CI green (including pip-audit + AI-BOM validation)
3. Staging smoke tests before production promotion
4. Merge commit (no squash) to integration branch

## Review cadence

| Artifact | Frequency | Owner |
|---|---|---|
| AI-BOM (`infrastructure/ai-bom.yaml`) | Weekly | Security |
| MITRE coverage doc | Quarterly | Security |
| OpenSSF Scorecard | Weekly (manual) | Security |
| Vendor reassessment (LLM providers) | 6 months | AI/ML Engineering |
| Agent manifest / prompt packs | On change | AI/ML Engineering |

## Emergency procedures

| Scenario | Immediate action |
|---|---|
| Prompt injection spike | `AI_FEATURES_ENABLED=false`; review DLQ |
| DLQ flood | Rate-limit AI endpoints; inspect `dlq_events` |
| Credential compromise | Rotate JWT secret; revoke MCP tokens; disable broker |
| MCP tool poisoning | Disable MCP integration; quarantine responses |

### AI kill switch

Set `AI_FEATURES_ENABLED=false` — all `/api/v1/ai/*` return **503**.

In-flight LangGraph runs: cancel with timeout (orchestrator handles partial state).

## Security documentation index

- [SECURITY.md](SECURITY.md) — defense framework
- [security/MITRE-ATTACK-COVERAGE.md](security/MITRE-ATTACK-COVERAGE.md)
- [security/incident-response-playbook.md](security/incident-response-playbook.md)
- [SUPPLY-CHAIN-SECURITY.md](SUPPLY-CHAIN-SECURITY.md)
- [DEPLOYMENT-GATES.md](DEPLOYMENT-GATES.md)
- [IDENTITY-PROPAGATION.md](IDENTITY-PROPAGATION.md)
- [AGENTIC-CONSENT.md](AGENTIC-CONSENT.md)

## Post-incident

Capture lessons in [tasks/lessons.md](tasks/lessons.md) using the template in the incident playbook.
