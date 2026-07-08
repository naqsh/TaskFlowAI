import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const notificationSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  user_id: z.string().uuid(),
  type: z.string(),
  title: z.string(),
  body: z.string(),
  resource_type: z.string(),
  resource_id: z.string().uuid().nullable(),
  read_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
});

export type Notification = z.infer<typeof notificationSchema>;

export const notificationListSchema = z.object({
  items: z.array(notificationSchema),
  total_unread: z.number().int(),
  limit: z.number().int(),
  offset: z.number().int(),
});

export const markReadResponseSchema = z.object({
  notification: notificationSchema,
});

export const markAllReadResponseSchema = z.object({
  updated: z.number().int(),
});

export type NotificationListResponse = z.infer<typeof notificationListSchema>;

export async function fetchNotifications(params: {
  limit: number;
  offset: number;
}): Promise<NotificationListResponse> {
  const data = await apiFetch<unknown>(
    `/api/v1/notifications?limit=${encodeURIComponent(params.limit)}&offset=${encodeURIComponent(
      params.offset,
    )}`,
  );
  return notificationListSchema.parse(data);
}

export async function markNotificationRead(notificationId: string): Promise<Notification> {
  const data = await apiFetch<unknown>(`/api/v1/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
  return markReadResponseSchema.parse(data).notification;
}

export async function markAllNotificationsRead(): Promise<number> {
  const data = await apiFetch<unknown>(`/api/v1/notifications/read-all`, {
    method: "POST",
  });
  return markAllReadResponseSchema.parse(data).updated;
}

