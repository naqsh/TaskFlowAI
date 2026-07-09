# Deployment Gates — TaskFlow AI (TF-059)

**Version:** 1.0.0 | **Last Updated:** July 2026

## Pipeline overview

```mermaid
flowchart LR
  merge[Merge to integration] --> build[Build + push GHCR]
  build --> sign[Cosign sign image]
  sign --> manifest[Sign agent manifest]
  manifest --> staging[Deploy staging]
  staging --> smoke[Smoke tests 3x retry]
  smoke --> canary[Canary 10% traffic]
  canary --> prod[Production rollout]
```

## Gate checklist

| Gate | Environment | Blocking | Verification |
|---|---|---|---|
| CI green | PR | ✅ | ruff, mypy, pytest, pip-audit, AI-BOM |
| Docker build | CI | ✅ | `infrastructure/Dockerfile` |
| Image sign | integration push | ✅ (when key set) | Cosign verify |
| Manifest sign | integration push | ✅ | `load_agent_manifest(require_signature=True)` |
| Staging deploy | staging | ✅ | GitHub `staging` environment |
| Smoke tests | staging | ✅ | `scripts/smoke_test_staging.py` |
| Canary | canary | ✅ | 10% traffic, 30 min soak |
| Production | production | ✅ | Manual workflow_dispatch |

## Smoke tests

```bash
uv run python scripts/smoke_test_staging.py https://staging-api.example.com
```

Checks:

- `GET /health` — 200
- `GET /metrics` — Prometheus scrape OK
- `GET /api/v1/ping` — API availability

Retries: **3** with 5s delay (flake tolerance).

## Rollback procedure

**RTO target:** <15 minutes

1. Revert merge commit on `epic/taskflow-implementation` or roll back to previous GHCR digest
2. `workflow_dispatch` deploy with previous image tag
3. Verify smoke tests against rolled-back staging
4. Disable AI if security incident: `AI_FEATURES_ENABLED=false`
5. Post-incident: [incident-response-playbook.md](security/incident-response-playbook.md)

## Canary auto-rollback triggers (documented)

| Signal | Threshold | Action |
|---|---|---|
| 5xx rate | >2% for 5 min | Roll back canary |
| p95 latency | >2× baseline | Roll back canary |
| `prompt_cache_hit_rate` | <50% sustained | Investigate warmer; roll back if regression |

## Secrets

Use GitHub **environments** (`staging`, `canary`, `production`) for:

- `STAGING_URL`
- `COSIGN_PRIVATE_KEY` / `COSIGN_PASSWORD`
- `AGENT_MANIFEST_PRIVATE_KEY`
- Production Supabase credentials (separate from staging)

## Related

- [SUPPLY-CHAIN-SECURITY.md](SUPPLY-CHAIN-SECURITY.md)
- [../infrastructure/AGENT.md](../infrastructure/AGENT.md)
