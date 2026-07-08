# Critic Agent (TF-033)

Role: Final safety and quality gate.

Rules (Part 2 MVP):
- Always run `InputSecurityScanner` over combined `planner_result` + `context_result`.
- If a security violation is found:
  - block immediately
  - return `status=escalated` with `security_violation_detected`
  - ensure `retry_allowed=false`
- Quality checks are advisory only:
  - vague titles trigger minor concerns but do not block the pipeline.
