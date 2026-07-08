import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const searchItemSchema = z.object({
  kind: z.enum(["task", "project", "comment"]),
  id: z.string().uuid(),
  title: z.string().nullable(),
  snippet: z.string().nullable(),
  created_at: z.string().datetime().nullable(),
  workspace_id: z.string().uuid().nullable().optional(),
});

export type SearchItem = z.infer<typeof searchItemSchema>;

export const searchResponseSchema = z.object({
  items: z.array(searchItemSchema),
  total: z.number().int(),
  q: z.string(),
});

export type SearchResponse = z.infer<typeof searchResponseSchema>;

export async function fetchSearch(params: {
  q: string;
  type?: "tasks" | "projects" | "comments" | "all";
  limit?: number;
  offset?: number;
  project_id?: string;
  status?: string;
  priority?: string;
}): Promise<SearchResponse> {
  const qs = new URLSearchParams();
  qs.set("q", params.q);
  if (params.type) qs.set("type", params.type);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  if (params.project_id) qs.set("project_id", params.project_id);
  if (params.status) qs.set("status", params.status);
  if (params.priority) qs.set("priority", params.priority);

  const data = await apiFetch<unknown>(`/api/v1/search?${qs.toString()}`);
  return searchResponseSchema.parse(data);
}

