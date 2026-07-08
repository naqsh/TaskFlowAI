Output schema (JSON only):
{
  "tasks": Array<{ "id": string, "title": string, "description": string | null, "priority": string, "due_date": string | null }>,
  "projects": Array<{ "id": string, "name": string, "description": string | null }>,
  "comments": Array<{ "id": string, "task_id": string, "body": string }>,
  "context_summary": string,
  "truncated": boolean
}

