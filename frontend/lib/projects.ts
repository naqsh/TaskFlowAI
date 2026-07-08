import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const projectSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  created_by: z.string().uuid().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const projectListSchema = z.object({
  items: z.array(projectSchema),
  limit: z.number(),
  offset: z.number(),
});

export type Project = z.infer<typeof projectSchema>;
export type ProjectListResponse = z.infer<typeof projectListSchema>;

export async function fetchProjects(
  limit = 50,
  offset = 0,
): Promise<Project[]> {
  const data = await apiFetch<unknown>(
    `/api/v1/projects?limit=${limit}&offset=${offset}`,
  );
  return projectListSchema.parse(data).items;
}

export async function fetchProject(projectId: string): Promise<Project> {
  const data = await apiFetch<unknown>(`/api/v1/projects/${projectId}`);
  return projectSchema.parse(data);
}

export async function createProject(payload: {
  name: string;
  description?: string | null;
}): Promise<Project> {
  const data = await apiFetch<unknown>(`/api/v1/projects`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return projectSchema.parse(data);
}

export async function updateProject(
  projectId: string,
  payload: { name?: string | null; description?: string | null },
): Promise<Project> {
  const data = await apiFetch<unknown>(`/api/v1/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return projectSchema.parse(data);
}

export async function deleteProject(projectId: string): Promise<void> {
  await apiFetch(`/api/v1/projects/${projectId}`, { method: "DELETE" });
}

