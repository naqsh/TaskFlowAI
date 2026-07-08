import { z } from "zod";

import { apiFetch } from "@/lib/api";

export const meSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  full_name: z.string(),
  workspace_id: z.string().uuid().nullable(),
});

export type Me = z.infer<typeof meSchema>;

export async function fetchMe(): Promise<Me> {
  const data = await apiFetch<unknown>(`/api/v1/auth/me`);
  return meSchema.parse(data);
}

