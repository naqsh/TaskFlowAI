# Lessons Learned — TaskFlow AI

Format: **Date | Mistake Pattern | Root Cause | Rule to Prevent Recurrence**

---

## Security

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-08 | Spotlighting marker spec drift | Used a non-canonical end marker string for external content | Keep `EXTERNAL_MARKER_*` constants aligned with spec (`<<<EXTERNAL_CONTENT>>>` … `<<</EXTERNAL_CONTENT>>>`) and rely on tests to catch drift |
| — | — | — | Check `docs/SECURITY.md` before agent I/O changes (when created) |

## Architecture

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| — | — | — | API → Service → Repository; no SQL in handlers |

## Testing

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-08 | Lint/type violations after refactor | Added new telemetry helper without return type annotation and introduced an overlong line failing ruff E501 | Run `uv run ruff check backend --fix` and `uv run mypy backend` immediately after refactors; only then proceed |
| — | — | — | Run full backend verification gate before marking backend tasks done |

## Workflow

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-08 | Lessons update gate too narrow | TaskFlow rules previously said to update lessons only after explicit user corrections; TF-011 included self-corrected mistakes surfaced by tooling | Update `docs/tasks/lessons.md` whenever a mistake is made or corrected (including self-corrections) |
| — | — | — | Write `todo.md` plan before implementation |

---

*TaskFlow AI Lessons — initialized at scaffold*
