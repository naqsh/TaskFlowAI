# Infrastructure AGENT.md — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

## Scope

CI/CD, Docker backend, deployment rules. Frontend deploys to Vercel (see TF-E7).

---

## GitHub Branch Policy

| Branch | Purpose |
|---|---|
| `epic/taskflow-implementation` | Long-lived integration branch |
| `epic/TF-E{n}-{name}` | Per-epic work branch |

Merge with **merge commit** after CI passes. Delete local epic branch; keep remote.

---

## CI Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | PR + push to integration | Lint, typecheck, test, docker build, pip-audit, AI-BOM |
| `.github/workflows/deploy.yml` | Push to integration + manual | Staging → smoke → canary → prod |

Cosign image signing and agent manifest signing in `deploy.yml` (TF-E6).

## Supply chain

- AI-BOM: `infrastructure/ai-bom.yaml`
- Agent manifest: `infrastructure/agent-manifest.json` (+ ed25519 signature)
- See [../docs/SUPPLY-CHAIN-SECURITY.md](../docs/SUPPLY-CHAIN-SECURITY.md) and [../docs/DEPLOYMENT-GATES.md](../docs/DEPLOYMENT-GATES.md)

---

## Docker

- **Backend only** — `infrastructure/Dockerfile` exposes port 8010
- **No frontend** in container — Vercel handles FE deploy
- Local stack: `docker compose -f infrastructure/docker-compose.yml up`

---

## Links

- [../docs/guidance/docker-setup.md](../docs/guidance/docker-setup.md)
- [../docs/TaskFlowAI_Project_Proposal.md](../docs/TaskFlowAI_Project_Proposal.md) § Deployment

---

*Infrastructure AGENT.md — TaskFlow AI — Version 0.1.0*
