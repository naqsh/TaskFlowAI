# MITRE ATT&CK for AI Systems — Coverage Mapping (TF-057)

**Version:** 1.0.0 | **Last Updated:** 2026-07-09  
**Review cadence:** Quarterly (next review: 2026-10-09)  
**MITRE reference:** [ATT&CK for AI Systems](https://atlas.mitre.org/) + OWASP LLM Top 10

## Summary

| Metric | Value |
|---|---|
| Applicable techniques | 12 |
| Covered | 11 |
| N/A (with rationale) | 1 |
| **Coverage** | **91.7%** (>80% target ✅) |

## Technique mapping

| ID | Technique | Coverage | Detection / control | Test reference |
|---|---|---|---|---|
| AML.T0051 | Prompt Injection | 95% | `InputSecurityScanner` (regex → PromptGuard 2 → constitutional) + Spotlighting | `backend/tests/security/test_security.py`, `test_spotlighting.py` |
| AML.T0054 | LLM Jailbreak | 95% | Constitutional classifier + jailbreak corpus (≥95% block) | `backend/tests/security/test_security.py` |
| AML.T0043 | Tool Poisoning | 90% | `MCPResponseValidator` schema + nh3 + anomaly quarantine | `backend/tests/security/test_tool_poisoning.py` |
| AML.T0053 | Excessive Agency | 85% | Delegation tokens + tool allowlists + `ToolManager` chain limits | `backend/tests/security/test_confused_deputy.py`, `test_identity_integration.py` |
| AML.T0048 | Confused Deputy | 90% | `DelegationContext` intent ↔ tool mapping in `ToolManager` | `backend/tests/security/test_confused_deputy.py` |
| AML.T0016 | Capability Theft | N/A | Model weights not hosted; vendor APIs only — theft not applicable | — |
| T1078 | Valid Accounts | 90% | JWT + RBAC + workspace scoping | `backend/tests/test_auth.py` |
| T1190 | Exploit Public-Facing Application | 85% | Input scanner + rate limiting + MCP URL allowlist | `backend/tests/security/test_security_integration.py` |
| T1566 | Phishing (AI-assisted) | 80% | Constitutional exfiltration rules + output sanitization | `backend/tests/security/test_constitutional.py` |
| LLM02 | Insecure Output Handling | 90% | nh3 sanitization on MCP responses | `backend/tests/security/test_tool_poisoning.py` |
| LLM07 | System Prompt Leakage | 85% | `system_prompt_exfiltration` constitutional rule | `backend/tests/security/test_constitutional.py` |
| AML.T0040 | RAG Poisoning | 75% | Quarantine stub when `FEATURE_VECTOR_SEARCH=true` | `backend/tests/security/test_rag_quarantine.py` |

## Gaps and remediation

| Technique | Gap | Remediation | Ticket |
|---|---|---|---|
| AML.T0040 | Full vector ingestion pipeline not implemented | Quarantine stub + ingestion review when RAG enabled | TF-E7+ |

## Uncovered / N/A rationale

- **AML.T0016 Capability Theft:** TaskFlow does not host proprietary model weights; inference uses vendor APIs or optional local Ollama. Marked N/A.

## Review process

1. Compare against latest MITRE ATLAS release notes
2. Update coverage % and test references
3. File tickets for gaps >1 sprint
4. Link updates in [SECURITY.md](../SECURITY.md)
