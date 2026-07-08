import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const commentSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  task_id: z.string().uuid(),
  author_id: z.string().uuid().nullable(),
  body: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const commentListSchema = z.object({
  items: z.array(commentSchema),
});

export type Comment = z.infer<typeof commentSchema>;

export async function fetchComments(taskId: string): Promise<Comment[]> {
  const data = await apiFetch<unknown>(`/api/v1/tasks/${taskId}/comments`);
  return commentListSchema.parse(data).items;
}

export async function createComment(taskId: string, body: string): Promise<Comment> {
  const data = await apiFetch<unknown>(`/api/v1/tasks/${taskId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
  return commentSchema.parse(data);
}

export async function updateComment(commentId: string, body: string): Promise<Comment> {
  const data = await apiFetch<unknown>(`/api/v1/comments/${commentId}`, {
    method: "PATCH",
    body: JSON.stringify({ body }),
  });
  return commentSchema.parse(data);
}

export async function deleteComment(commentId: string): Promise<void> {
  await apiFetch(`/api/v1/comments/${commentId}`, { method: "DELETE" });
}
