# Supply Chain Security — TaskFlow AI (TF-055 / TF-056)

**Version:** 1.0.0 | **Last Updated:** July 2026

## AI Bill of Materials (AI-BOM)

| Artifact | Path | Purpose |
|---|---|---|
| Manifest | `infrastructure/ai-bom.yaml` | Models + production libraries in use |
| Validator | `backend/security/bom.py` | Load + freshness checks |
| CI CLI | `scripts/validate_ai_bom.py` | Fail when runtime models or deps drift |

### Update cadence

- **Owner:** Platform Security
- **Frequency:** Weekly (or on any model / dependency change)
- **Stale threshold:** >7 days triggers CI warning (`--warn-stale`)

### Local validation

```bash
uv run python scripts/validate_ai_bom.py
uv run python scripts/validate_ai_bom.py --warn-stale
```

## pip-audit CI gate

CI runs `scripts/pip_audit_gate.py`, which audits **production** dependencies (via `uv export --no-dev`) and **blocks** merges on **CRITICAL** or **HIGH** CVEs.

### CVE without fix

Document an ADR exception with expiry date in `docs/adr/` (see `ADR-003-ecdsa-pip-audit-exception.md`) and add the ID to `IGNORED_VULN_IDS` in `scripts/pip_audit_gate.py`.

## OpenSSF Scorecard

| Policy | Threshold |
|---|---|
| Minimum score | **≥ 7.0** |

Scorecard CLI is run **manually weekly** (not in every PR). Required checks include:

- `SECURITY.md` at repo root
- Dependabot configuration
- Branch protection on integration branch

```bash
# Manual weekly audit (requires scorecard CLI installed)
scorecard --repo=github.com/org/taskflow-ai
```

## Dependabot

Configuration: `.github/dependabot.yml` — weekly updates for Python (`uv.lock`) and npm (`frontend/package-lock.json`).

## Agent manifest signing (TF-060)

| Artifact | Path |
|---|---|
| Manifest | `infrastructure/agent-manifest.json` |
| Signature | `infrastructure/agent-manifest.sig` |
| Public key(s) | `infrastructure/keys/agent-manifest.pub` |

CI signs with `AGENT_MANIFEST_PRIVATE_KEY` (ed25519 PEM). Production (`APP_ENV=production`) rejects unsigned manifests.

### Key rotation

1. Add new public key to `infrastructure/keys/` (support two keys during transition)
2. Re-sign manifest in CI
3. Remove old public key after all running instances verify with new key

## Docker image signing (TF-062)

Production images pushed to GHCR are signed with **Cosign** in `.github/workflows/deploy.yml`.
Verify with:

```bash
cosign verify --key infrastructure/keys/cosign.pub ghcr.io/org/taskflow-ai-backend:latest
```

## Related

- [SECURITY.md](../SECURITY.md)
- [DEPLOYMENT-GATES.md](DEPLOYMENT-GATES.md)
- [GOVERNANCE.md](GOVERNANCE.md)
