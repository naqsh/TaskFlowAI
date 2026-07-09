# MVP 6 Production Proof — TaskFlow AI (TF-062)

**Date:** 2026-07-09  
**Branch:** `epic/TF-E6-production`

## Checklist

- [x] AI-BOM validates (`scripts/validate_ai_bom.py`)
- [x] pip-audit policy in CI (CRITICAL/HIGH block)
- [x] MITRE coverage doc >80% (91.7%)
- [x] PromptCacheWarmer implemented + tests
- [x] Agent manifest ed25519 signing + verification
- [x] Deployment gates documented + `deploy.yml`
- [x] Governance + incident playbook
- [x] AI kill switch (`AI_FEATURES_ENABLED=false` → 503)
- [x] RAG quarantine stub (`FEATURE_VECTOR_SEARCH`)
- [x] Cosign sign step in deploy workflow (when key configured)
- [x] Full pytest suite green — **207 passed**, 29 skipped (`proof/mvp6/pytest-mvp6.txt`)

## Artifacts

| File | Description |
|---|---|
| `pytest-mvp6.txt` | Full backend test run output |
| `checklist.md` | This file |

## Cache hit rate

Target >70% with `CACHE_WARMING_ENABLED=true` under load test.
Warmer unit tests verify `cache_read_tokens` on repeat calls (mock provider).

## Cosign verify

```bash
# After deploy with COSIGN_PRIVATE_KEY configured
cosign verify --key infrastructure/keys/cosign.pub ghcr.io/<org>/taskflow-ai-backend:latest
```

Public cosign key placeholder: configure in CI secrets for production.
