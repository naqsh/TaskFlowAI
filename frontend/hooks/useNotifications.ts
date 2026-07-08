"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
  type NotificationListResponse,
} from "@/lib/notifications";

export function useNotifications(params: {
  limit: number;
  offset: number;
  enabled?: boolean;
}) {
  const queryClient = useQueryClient();
  const enabled = params.enabled ?? true;

  const list = useQuery<NotificationListResponse>({
    queryKey: ["notifications", params.limit, params.offset],
    queryFn: () => fetchNotifications(params),
    enabled,
    refetchInterval: 30_000,
  });

  const markOne = useMutation({
    mutationFn: (notificationId: string) => markNotificationRead(notificationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAll = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return {
    notifications: list.data?.items ?? [],
    totalUnread: list.data?.total_unread ?? 0,
    isLoading: list.isLoading,
    error: list.error,
    markOne,
    markAll,
  };
}

export type { Notification };

