# ADR-003: pip-audit exception for python-ecdsa (CVE-2024-23342)

**Status:** Accepted  
**Date:** 2026-07-09  
**Expires:** 2026-12-31 (reassess when python-jose or ecdsa publishes a fix)

## Context

`python-jose` (JWT signing) depends on `ecdsa`, which has **PYSEC-2026-1325** / **CVE-2024-23342** — a Minerva timing attack on P-256 with **no fix version** published. The upstream project considers side-channel attacks out of scope.

## Decision

CI `scripts/pip_audit_gate.py` ignores this vulnerability ID set while continuing to block all other **CRITICAL** and **HIGH** findings in production dependencies.

## Consequences

- pip-audit gate remains enabled for all other production CVEs
- Revisit before expiry or when `python-jose` migrates off `ecdsa`
- Runtime mitigation: JWT verification only (signing uses HS256 in dev; production should prefer asymmetric keys with audited libraries)

## References

- `scripts/pip_audit_gate.py` — `IGNORED_VULN_IDS`
- [docs/SUPPLY-CHAIN-SECURITY.md](../SUPPLY-CHAIN-SECURITY.md)
