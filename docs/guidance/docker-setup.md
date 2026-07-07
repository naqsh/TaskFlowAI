# Docker Backend Setup — TaskFlow AI

**Status:** Stub — expand during TF-E7 hybrid deploy

---

## Local backend container

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

Backend API: http://localhost:8010/health

---

## Notes

- Frontend deploys to **Vercel** separately — not bundled in this Docker image
- Use `infrastructure/nginx.conf` for local hybrid testing (proxy `/api` to FastAPI)
- Production images publish to GHCR (MVP 6)

---

*Guidance stub — TaskFlow AI*
