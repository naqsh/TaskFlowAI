# Agentic Consent — TaskFlow AI (TF-051)

## Overview

Time-bounded AI consent records enforce user authorization before any AI endpoint invocation. Consent is workspace-scoped and stored server-side.

## Consent Record

| Field | Description |
|---|---|
| `user_id` | User who granted consent |
| `workspace_id` | Workspace scope |
| `scope` | `ai_assistance` (minimal: read_tasks, read_projects) |
| `granted_at` | Grant timestamp |
| `expires_at` | 30-day default TTL |
| `revoked_at` | Set on explicit revoke |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/consent/ai` | Grant AI consent |
| `GET` | `/api/v1/consent/ai` | Check consent status |
| `DELETE` | `/api/v1/consent/ai` | Revoke consent immediately |

## Enforcement

All `/api/v1/ai/*` endpoints call `ConsentService.is_valid()` before graph invoke. Missing consent returns HTTP 403 with `error: consent_required`.

## Frontend

`ConsentPromptModal` in `AITaskCreator` calls `POST /api/v1/consent/ai` on accept before invoking AI.

## Edge Cases

- Grant while revoked: new record supersedes prior
- Admin cannot grant consent for another user (JWT-scoped)
- GDPR user delete: cascade via `users.id` FK

## Files

- `backend/services/consent_service.py`
- `backend/api/v1/consent.py`
- `backend/api/v1/ai.py`
- `frontend/lib/consent.ts`
