# Try TaskFlow AI Locally

**Status:** Scaffold quickstart

---

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Redis (optional for MVP 1 scaffold; required for auth sessions later)

---

## Backend

```bash
cp .env.example .env
py -m uv sync
py -m uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8010
```

Verify:

```bash
curl http://localhost:8010/health
curl http://localhost:8010/api/v1/ping
```

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

Set `NEXT_PUBLIC_API_URL=http://localhost:8010` in `frontend/.env.local` (or root `.env` for local dev).

---

## Hybrid local test

1. Start backend on port 8010
2. Start frontend on port 3000 with `NEXT_PUBLIC_API_URL=http://localhost:8010`
3. Dashboard shows backend connectivity status

---

*Guidance — TaskFlow AI*
