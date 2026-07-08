"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchEmailNotificationsPrefs,
  type EmailNotificationsPrefs,
  updateEmailNotificationsPrefs,
} from "@/lib/preferences";

export function useEmailNotificationsPrefs() {
  const queryClient = useQueryClient();

  const pref = useQuery<EmailNotificationsPrefs>({
    queryKey: ["email-notifications-pref"],
    queryFn: fetchEmailNotificationsPrefs,
  });

  const update = useMutation({
    mutationFn: (enabled: boolean) =>
      updateEmailNotificationsPrefs({ email_notifications_enabled: enabled }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["email-notifications-pref"] });
    },
  });

  return {
    emailNotificationsEnabled: pref.data?.email_notifications_enabled ?? true,
    isLoading: pref.isLoading,
    error: pref.error,
    update,
  };
}

