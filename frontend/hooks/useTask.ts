 "use client";

 import { useQuery } from "@tanstack/react-query";

 import { fetchTask, type Task } from "@/lib/tasks";

 export function useTask(taskId: string) {
   return useQuery({
     queryKey: ["task", taskId],
     queryFn: () => fetchTask(taskId),
     enabled: Boolean(taskId),
   });
 }

 export type { Task };

