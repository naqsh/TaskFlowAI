# Security Policy — TaskFlow AI

**Version:** 1.0.0 | **Last Updated:** July 2026

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |

## Reporting a vulnerability

Email **security@taskflow-ai.local** with:

- Description and reproduction steps
- Affected component (backend API, frontend, MCP, infrastructure)
- Severity assessment (if known)

We aim to acknowledge reports within **48 hours** and provide a remediation timeline within **7 days** for confirmed issues.

## Security practices

- Dependency scanning via **pip-audit** (backend) in CI — blocks **CRITICAL** and **HIGH** CVEs
- OpenSSF Scorecard policy: minimum **7.0** (manual weekly audit; see [docs/SUPPLY-CHAIN-SECURITY.md](docs/SUPPLY-CHAIN-SECURITY.md))
- Automated dependency updates via **Dependabot**
- AI Bill of Materials: [infrastructure/ai-bom.yaml](infrastructure/ai-bom.yaml)
- Agent config signing: [infrastructure/agent-manifest.json](infrastructure/agent-manifest.json)

## Disclosure

Please do not open public GitHub issues for undisclosed security vulnerabilities.

## Related documentation

- [docs/SECURITY.md](docs/SECURITY.md) — defense-in-depth framework
- [docs/security/MITRE-ATTACK-COVERAGE.md](docs/security/MITRE-ATTACK-COVERAGE.md)
- [docs/GOVERNANCE.md](docs/GOVERNANCE.md)
