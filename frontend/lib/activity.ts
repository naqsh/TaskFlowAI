import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const activityEventSchema = z.object({
  id: z.string().uuid(),
  actor_id: z.string().uuid().nullable(),
  action: z.string(),
  resource_type: z.string(),
  resource_id: z.string().uuid().nullable(),
  summary: z.string(),
  created_at: z.string().datetime(),
});

export type ActivityEvent = z.infer<typeof activityEventSchema>;

export const activityListSchema = z.object({
  items: z.array(activityEventSchema),
  limit: z.number().int(),
  offset: z.number().int(),
});

export type ActivityListResponse = z.infer<typeof activityListSchema>;

export async function fetchProjectActivity(projectId: string, params: { limit: number; offset: number }) {
  const qs = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
  });
  return activityListSchema.parse(
    await apiFetch<unknown>(`/api/v1/projects/${projectId}/activity?${qs.toString()}`),
  );
}

export async function fetchTaskActivity(taskId: string, params: { limit: number; offset: number }) {
  const qs = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
  });
  return activityListSchema.parse(
    await apiFetch<unknown>(`/api/v1/tasks/${taskId}/activity?${qs.toString()}`),
  );
}

