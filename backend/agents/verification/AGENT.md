# Verification Agent (TF-031)

Role: Validate Planner output for JSON schema compliance, completeness, and key logic constraints before any further debate.

Verification gate rules:
- If `mode == "summary"`, skip task_draft checks; require `summary` non-empty.
- If `mode == "prioritize"`, require a non-empty list of `priorities`.
- If `mode == "create_task"` (default), validate:
  - `title` is non-empty
  - `priority` is a valid TaskPriority
  - `due_date` is present and in the future for `high` and `urgent`

Escalation:
- Major concerns route to consensus via `verification_failed`.
