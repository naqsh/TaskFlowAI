import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const emailNotificationsPrefsSchema = z.object({
  email_notifications_enabled: z.boolean(),
});

export type EmailNotificationsPrefs = z.infer<typeof emailNotificationsPrefsSchema>;

export async function fetchEmailNotificationsPrefs(): Promise<EmailNotificationsPrefs> {
  const data = await apiFetch<unknown>(`/api/v1/preferences/email-notifications`);
  return emailNotificationsPrefsSchema.parse(data);
}

export async function updateEmailNotificationsPrefs(payload: {
  email_notifications_enabled: boolean;
}): Promise<EmailNotificationsPrefs> {
  const data = await apiFetch<unknown>(`/api/v1/preferences/email-notifications`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return emailNotificationsPrefsSchema.parse(data);
}

