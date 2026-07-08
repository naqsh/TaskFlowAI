import { z } from "zod";

import { apiFetch } from "@/lib/api";
import { taskPrioritySchema } from "@/lib/tasks";

export const aiResponseSchema = z.object({
  status: z.enum(["success", "degraded", "failure"]),
  trace_id: z.string(),
  data: z.object({
    mode: z.enum(["create_task", "summary", "prioritize"]).nullable(),
    task_draft: z
      .object({
        title: z.string(),
        priority: taskPrioritySchema,
        due_date: z.string().nullable(),
      })
      .nullable(),
    summary: z.string().nullable(),
    priorities: z.array(z.string()).nullable(),
  }),
  metadata: z.object({
    trace_id: z.string(),
    execution_ms: z.number().int().nonnegative(),
    tokens_used: z.number().int().nonnegative(),
    model_used: z.string().nullable(),
    prompt_version: z.string().nullable(),
    agents_executed: z.array(z.string()),
    cache_hit_rate: z.number().nonnegative().nullable(),
    consensus_status: z.string().nullable(),
    reason: z.string().nullable(),
  }),
});

export type AIResponse = z.infer<typeof aiResponseSchema>;
export type AITaskDraft = NonNullable<AIResponse["data"]["task_draft"]>;

export async function parseTaskWithAI(nl_input: string): Promise<AIResponse> {
  const data = await apiFetch<unknown>(`/api/v1/ai/parse-task`, {
    method: "POST",
    body: JSON.stringify({ nl_input }),
  });
  return aiResponseSchema.parse(data);
}

export async function summarizeProjectWithAI(nl_input: string): Promise<AIResponse> {
  const data = await apiFetch<unknown>(`/api/v1/ai/summarize`, {
    method: "POST",
    body: JSON.stringify({ nl_input }),
  });
  return aiResponseSchema.parse(data);
}

