1) If mode is summary: validate summary non-empty; skip task checks.
2) If mode is prioritize: validate priorities list non-empty.
3) If mode is create_task:
   - title must be non-empty
   - priority must be a valid enum
   - due_date must be in the future for high/urgent
Return JSON with concerns[] (empty = pass).

