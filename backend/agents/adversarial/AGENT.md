# Adversarial Agent (TF-032)

Role: Challenge Planner assumptions and surface edge cases before Critic/Consensus.

Deterministic edge checks (MVP for Part 2):
- Overdue `due_date` for new `create_task` => major concern
- Unrealistic workload proxy:
  - if >= 10 context tasks have `due_date == task_draft.due_date` and `priority == high`,
    flag a major concern.

Escalation:
- Any major concern routes to consensus via `adversarial_concerns` with `retry_allowed=true`.
