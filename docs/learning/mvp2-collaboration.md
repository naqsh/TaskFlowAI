# MVP 2 Collaboration — Learning Notes (TF-E2)

## Notifications
- Emit notifications from domain services immediately after state changes (task assignment and comment creation).
- Store notification metadata in the DB and drive the UI from unread lists (`read_at IS NULL`).
- Prefer “fail-open” email behavior: if email sending fails (or is disabled), still create the in-app notification.

## Attachments
- Validate MIME type with an allowlist early in the service layer; reject unsupported uploads with `415`.
- Enforce a hard server-side size cap (<10MB) and return `413` for oversized payloads.
- Use signed, time-limited download tokens for authorization instead of relying on user auth at download time.

## Activity timeline
- Derive the activity feed from the existing append-only `audit_logs` table.
- Ensure every event that should appear in the timeline is logged with:
  - `resource_type` and `resource_id` (when applicable), and/or
  - `metadata.task_id` when the event is not a direct task resource.

## Search & filters
- Keep search “workspace-scoped” and avoid leaking cross-workspace rows.
- Return empty result sets with `total=0` instead of errors when the query is empty or yields no matches.

## Redis & rate limiting
- Implement 429 behavior behind a middleware gate for `/api/v1/*` (excluding auth + health).
- Degrade gracefully when Redis is unavailable by falling back to an in-memory limiter.
- Add headers (`X-RateLimit-Remaining`, `Retry-After`) so the frontend can provide better UX.

