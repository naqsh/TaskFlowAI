Return strict JSON:
{
  "mode": "create_task" | "summary" | "prioritize",
  "task_draft": { "title": string, "priority": string, "due_date": string | null } | null,
  "summary": string | null,
  "priorities": string[] | null
}

