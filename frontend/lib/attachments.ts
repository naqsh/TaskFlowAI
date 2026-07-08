import { z } from "zod";

import { apiFetch, getApiBase, getAuthToken } from "@/lib/api";

export const attachmentSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  task_id: z.string().uuid(),
  uploaded_by: z.string().uuid().nullable(),
  filename: z.string(),
  mime_type: z.string(),
  size_bytes: z.number().int(),
  storage_key: z.string(),
  created_at: z.string().datetime(),
  download_url: z.string(),
});

export type Attachment = z.infer<typeof attachmentSchema>;

export const attachmentListSchema = z.object({
  items: z.array(attachmentSchema),
  limit: z.number().int(),
  offset: z.number().int(),
});

export type AttachmentListResponse = z.infer<typeof attachmentListSchema>;

export async function fetchTaskAttachments(taskId: string, params: {
  limit: number;
  offset: number;
}): Promise<AttachmentListResponse> {
  const qs = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
  });
  const data = await apiFetch<unknown>(`/api/v1/tasks/${taskId}/attachments?${qs.toString()}`);
  return attachmentListSchema.parse(data);
}

export async function uploadTaskAttachment(taskId: string, file: File): Promise<Attachment> {
  const base = getApiBase();
  if (!base) throw new Error("NEXT_PUBLIC_API_URL is not configured");

  const form = new FormData();
  form.append("file", file);

  const token = getAuthToken();
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const res = await fetch(`${base}/api/v1/tasks/${taskId}/attachments`, {
    method: "POST",
    headers,
    body: form,
  });

  if (!res.ok) {
    throw new Error(`Upload failed (${res.status})`);
  }

  const data = (await res.json()) as unknown;
  return attachmentSchema.parse(data);
}

