 "use client";

 import { useQuery } from "@tanstack/react-query";

 import { fetchTasks, type Task, type TaskPriority, type TaskStatus } from "@/lib/tasks";

 export function useTasks(params: {
   projectId?: string | null;
   status?: TaskStatus | null;
   priority?: TaskPriority | null;
   limit?: number;
   offset?: number;
 }) {
   const limit = params.limit ?? 50;
   const offset = params.offset ?? 0;

   return useQuery({
     queryKey: ["tasks", params.projectId ?? null, params.status ?? null, params.priority ?? null, limit, offset],
     queryFn: () =>
       fetchTasks({
         projectId: params.projectId ?? null,
         status: params.status ?? null,
         priority: params.priority ?? null,
         limit,
         offset,
       }),
   });
 }

 export type { Task };

