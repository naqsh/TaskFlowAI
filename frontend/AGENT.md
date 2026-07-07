# Frontend AGENT.md — TaskFlow AI

**Version:** 0.1.0 | **Last Updated:** July 2026

---

## Scope

Next.js 16 frontend deployed to **Vercel**. Consumes Docker-hosted FastAPI backend via `NEXT_PUBLIC_API_URL`.

---

## Technology Stack

| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16.x | App Router, Server Components |
| React | 19.x | UI |
| Tailwind CSS | 4.x | Styling via `@theme` |
| TanStack Query | 5.x | Data fetching (TF-010+) |
| React Hook Form + Zod | Latest | Forms (TF-010+) |
| DOMPurify | Latest | XSS prevention (client components only) |

---

## Deployment

- **Vercel native** — do NOT use `output: 'standalone'`
- Set `NEXT_PUBLIC_API_URL` to production Docker backend URL
- No LangGraph/MCP in frontend bundle

---

## Rules

| Rule | Behaviour |
|---|---|
| Server Components first | Client Components only for interactivity |
| Type safety | Zod-validate API responses before use |
| Sanitization | DOMPurify before rendering user HTML |
| Accessibility | WCAG 2.2 AA — keyboard nav, ARIA labels |
| Config errors | Show dev banner when `NEXT_PUBLIC_API_URL` unset |

---

## Verification Gate

```bash
npm run lint && npm run build
cd .. && uv run pytest  # when backend integration tests exist
```

Vitest coverage gate (>75%) enforced from TF-010 onward.

---

## Links

- [../AGENT.md](../AGENT.md)
- [../docs/TaskFlowAI_Project_Proposal.md](../docs/TaskFlowAI_Project_Proposal.md)

---

*Frontend AGENT.md — TaskFlow AI — Version 0.1.0*
