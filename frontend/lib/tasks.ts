import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const taskStatusSchema = z.enum([
  "todo",
  "in_progress",
  "done",
  "archived",
]);
export type TaskStatus = z.infer<typeof taskStatusSchema>;

export const taskPrioritySchema = z.enum(["low", "medium", "high", "urgent"]);
export type TaskPriority = z.infer<typeof taskPrioritySchema>;

export const taskSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  project_id: z.string().uuid(),
  title: z.string(),
  description: z.string().nullable(),
  status: taskStatusSchema,
  priority: taskPrioritySchema,
  due_date: z.string().nullable(),
  assignee_id: z.string().uuid().nullable(),
  created_by: z.string().uuid().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  warnings: z.array(z.string()),
});

export const taskListSchema = z.object({
  items: z.array(taskSchema),
  limit: z.number(),
  offset: z.number(),
});

export type Task = z.infer<typeof taskSchema>;
export type TaskListResponse = z.infer<typeof taskListSchema>;

export async function fetchTasks(params: {
  projectId?: string | null;
  status?: TaskStatus | null;
  priority?: TaskPriority | null;
  limit?: number;
  offset?: number;
}): Promise<Task[]> {
  const limit = params.limit ?? 50;
  const offset = params.offset ?? 0;

  const query = new URLSearchParams();
  query.set("limit", String(limit));
  query.set("offset", String(offset));

  if (params.projectId) query.set("project_id", params.projectId);
  if (params.status) query.set("status", params.status);
  if (params.priority) query.set("priority", params.priority);

  const data = await apiFetch<unknown>(`/api/v1/tasks?${query.toString()}`);
  return taskListSchema.parse(data).items;
}

export async function fetchTask(taskId: string): Promise<Task> {
  const data = await apiFetch<unknown>(`/api/v1/tasks/${taskId}`);
  return taskSchema.parse(data);
}

export async function createTask(payload: {
  project_id: string;
  title: string;
  description?: string | null;
  priority: TaskPriority;
  due_date?: string | null;
  assignee_id?: string | null;
}): Promise<Task> {
  const data = await apiFetch<unknown>(`/api/v1/tasks`, {
    method: "POST",
    body: JSON.stringify({
      project_id: payload.project_id,
      title: payload.title,
      description: payload.description ?? null,
      priority: payload.priority,
      due_date: payload.due_date ?? null,
      assignee_id: payload.assignee_id ?? null,
    }),
  });
  return taskSchema.parse(data);
}

export async function updateTask(
  taskId: string,
  payload: Partial<{
    title: string | null;
    description: string | null;
    status: TaskStatus | null;
    priority: TaskPriority | null;
    due_date: string | null;
    assignee_id: string | null;
  }>,
): Promise<Task> {
  const data = await apiFetch<unknown>(`/api/v1/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return taskSchema.parse(data);
}

export async function archiveTask(taskId: string): Promise<Task> {
  const data = await apiFetch<unknown>(`/api/v1/tasks/${taskId}`, {
    method: "DELETE",
  });
  return taskSchema.parse(data);
}

