# Supabase Setup — TaskFlow AI

**Status:** Active — TF-005

---

## 1. Create Supabase Project

1. Create a project at [https://supabase.com](https://supabase.com)
2. Open **Project Settings → Database**
3. Copy the **Supavisor pooler** connection string (port **6543**) for async SQLAlchemy

---

## 2. Configure Environment

Set in `.env` (see `.env.example`):

```env
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
```

### Password special characters

If your database password contains `@`, `#`, `/`, or other reserved URL characters, **percent-encode** them in `DATABASE_URL`:

| Character | Encoded |
|-----------|---------|
| `@` | `%40` |
| `#` | `%23` |
| `/` | `%2F` |

Example: password `p@ss#word` → `p%40ss%23word`

---

## 3. Supavisor + asyncpg

TaskFlow uses **async SQLAlchemy** with **asyncpg**. Supavisor transaction pooling requires:

```python
connect_args={"statement_cache_size": 0}
```

This is applied automatically in `backend/db/session.py` when the host is `*.supabase.com` or port is `6543`.

`prepare_database_url()` also strips libpq `sslmode` query params and maps them to asyncpg `ssl=require`.

---

## 4. Run Migrations

From the repo root:

```bash
uv sync
uv run alembic upgrade head
```

Rollback (if needed):

```bash
uv run alembic downgrade base
```

---

## 5. Schema Overview

| Table | Tenant scope | Notes |
|-------|--------------|-------|
| `users` | Global | Credentials (TF-006) |
| `workspaces` | Global | Tenant root |
| `workspace_members` | `workspace_id` | Role: admin, manager, member |
| `projects` | `workspace_id` | FK to workspace |
| `tasks` | `workspace_id` | Denormalized for RLS |
| `comments` | `workspace_id` | Denormalized for RLS |
| `audit_logs` | `workspace_id` (nullable) | Append-only trail |

All primary keys are **UUID**.

---

## 6. Row-Level Security (RLS)

Enable RLS on all tenant tables in the Supabase SQL editor after running migrations.

### Helper: current workspace from JWT

TF-006 will pass `workspace_id` via JWT claims. For RLS, use a session variable set by the backend before queries:

```sql
-- Set per-request from FastAPI (TF-007+)
SELECT set_config('app.workspace_id', '<workspace-uuid>', true);
SELECT set_config('app.user_id', '<user-uuid>', true);
```

### Example policies

```sql
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

-- Projects: members of the workspace can read
CREATE POLICY projects_select ON projects
  FOR SELECT
  USING (
    workspace_id::text = current_setting('app.workspace_id', true)
  );

-- Tasks: workspace-scoped read
CREATE POLICY tasks_select ON tasks
  FOR SELECT
  USING (
    workspace_id::text = current_setting('app.workspace_id', true)
  );

-- Comments: workspace-scoped read
CREATE POLICY comments_select ON comments
  FOR SELECT
  USING (
    workspace_id::text = current_setting('app.workspace_id', true)
  );

-- Workspace members: user can see own memberships
CREATE POLICY workspace_members_select ON workspace_members
  FOR SELECT
  USING (
    user_id::text = current_setting('app.user_id', true)
  );
```

Write policies for `INSERT`, `UPDATE`, and `DELETE` are added in **TF-007** (RBAC/ABAC) with role-aware checks.

---

## 7. Integration Tests

To run database integration tests locally:

```bash
# After alembic upgrade head against a test database
export TEST_DATABASE_URL="postgresql+asyncpg://..."
uv run pytest backend/tests/test_db_integration.py -m integration
```

Without `TEST_DATABASE_URL`, integration tests are skipped automatically.

---

*Supabase Setup — TaskFlow AI — TF-005*
