# Lessons Learned — TaskFlow AI

Format: **Date | Mistake Pattern | Root Cause | Rule to Prevent Recurrence**

---

## Security

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-09 | CredentialBroker scaffold without MCP hot-path wiring | TF-E5 marked done; broker unit tests passed but `graph/factory.py` never passed broker into `ToolManager` | After identity epic work, trace `execute_tool` → MCP and confirm JIT `access_token` injection, not only `vault.py` unit tests |
| 2026-07-09 | pip-audit CI used invalid flags and missing dev group | `pip-audit` was only in optional-dependencies; CI ran `--group dev` and used nonexistent `--fail-on` | Add `pip-audit` to `[dependency-groups] dev`, run `scripts/pip_audit_gate.py` (prod export + documented ignores) |
| 2026-07-09 | AI-BOM missing pyproject deps on first validate | Initial BOM listed core libs but omitted `python-multipart` and `types-PyYAML` | Run `uv run python scripts/validate_ai_bom.py` after any `pyproject.toml` dependency change |
| 2026-07-08 | Epic marked done with scaffold-only integrations | DLQ/quarantine/audit paths existed but were not wired through AI graph hot path | After security epic work, audit runtime call graph — not just file presence and unit tests |
| 2026-07-08 | Spotlighting marker spec drift | Used a non-canonical end marker string for external content | Keep `EXTERNAL_MARKER_*` constants aligned with spec (`<<<EXTERNAL_CONTENT>>>` … `<<</EXTERNAL_CONTENT>>>`) and rely on tests to catch drift |
| 2026-07-08 | Epic branch corruption during edit | Accidental partial replace in `graph/builder.py` while adding DLQ gate | After multi-hunk edits to pipeline files, re-read the full function before running tests |
| — | — | — | Check `docs/SECURITY.md` before agent I/O changes |

## Architecture

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-08 | Marking epic complete without ticket tests | Part 2 scaffold existed and todo was checked off before TF-031..040 testing criteria existed | Never mark TF-* done until ticket TESTING CRITERIA have dedicated tests; treat existing checkboxes as provisional until proof |
| 2026-07-08 | AIResponse Zod mismatch (optional keys omitted) | Orchestrator only emitted present fields (`task_draft` absent vs `null`) | Always emit stable schema keys (`null` placeholders) for API/FE contracts |
| — | — | — | API → Service → Repository; no SQL in handlers |

## Testing

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-16 | Full pytest blocked by nh3 native DLL App Control policy | Windows Application Control blocked `.venv` nh3 extension; conftest imports `create_app` → nh3 | On locked-down hosts, prove ADR-004 with `uv run pytest backend/tests/test_adr004_refactoring.py --noconftest`; still run full suite where App Control allows |
| 2026-07-08 | Lint/type violations after refactor | Added new telemetry helper without return type annotation and introduced an overlong line failing ruff E501 | Run `uv run ruff check backend --fix` and `uv run mypy backend` immediately after refactors; only then proceed |
| 2026-07-08 | Frontend auto-applied AI draft without preview confirm | Initial AITaskCreator applied draft on generate, skipping TF-040 preview→confirm flow | Keep AI draft in preview state until explicit “Use draft” |
| — | — | — | Run full backend verification gate before marking backend tasks done |

## Workflow

| Date | Mistake Pattern | Root Cause | Rule |
|---|---|---|---|
| 2026-07-08 | Lessons update gate too narrow | TaskFlow rules previously said to update lessons only after explicit user corrections; TF-011 included self-corrected mistakes surfaced by tooling | Update `docs/tasks/lessons.md` whenever a mistake is made or corrected (including self-corrections) |
| — | — | — | Write `todo.md` plan before implementation |

---

*TaskFlow AI Lessons — initialized at scaffold*
