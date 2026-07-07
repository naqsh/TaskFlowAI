# Supabase Setup — TaskFlow AI

**Status:** Stub — expand during TF-005

---

## Steps (overview)

1. Create Supabase project at https://supabase.com
2. Copy connection string — use **Supavisor pooler** port **6543** for async SQLAlchemy
3. Set `DATABASE_URL=postgresql+asyncpg://...` in `.env`
4. Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` for Auth integration (TF-006)
5. Run `uv run alembic upgrade head` after migrations exist

---

## Supavisor note

Async SQLAlchemy requires `statement_cache_size=0` on the engine — documented in TF-005.

---

## RLS

All tenant tables include `workspace_id`. RLS policies enforce isolation per workspace.

---

*Guidance stub — TaskFlow AI*
