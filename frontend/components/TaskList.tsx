 "use client";

 import { useMutation, useQueryClient } from "@tanstack/react-query";
 import { useRouter } from "next/navigation";
 import Link from "next/link";
 import { useEffect, useMemo, useState } from "react";

 import { ApiError } from "@/lib/api";
 import { Badge } from "@/components/ui/badge";
 import { Button } from "@/components/ui/button";
 import { Select } from "@/components/ui/select";
 import { TaskForm } from "@/components/TaskForm";
 import { archiveTask, updateTask, type Task, type TaskStatus } from "@/lib/tasks";
 import { useTasks } from "@/hooks/useTasks";

 const TASKS_LIMIT = 100;
 const TASKS_OFFSET = 0;

 export function TaskList({ projectId }: { projectId: string }) {
   const router = useRouter();
   const queryClient = useQueryClient();
   const tasksQueryKey = useMemo(
     () => ["tasks", projectId, null, null, TASKS_LIMIT, TASKS_OFFSET] as const,
     [projectId],
   );

   const { data: tasks = [], isLoading, error } = useTasks({
     projectId,
     limit: TASKS_LIMIT,
     offset: TASKS_OFFSET,
   });

   const [open, setOpen] = useState(false);

   useEffect(() => {
     if (!error) return;
     if (error instanceof ApiError && error.status === 401) {
       router.push("/login");
     }
   }, [error, router]);

   const [updateMessage, setUpdateMessage] = useState<string | null>(null);

   const updateStatus = useMutation({
     mutationFn: (vars: { taskId: string; status: TaskStatus }) =>
       updateTask(vars.taskId, { status: vars.status }),
     onMutate: async (vars) => {
       setUpdateMessage(null);
       await queryClient.cancelQueries({ queryKey: tasksQueryKey });
       const previous = queryClient.getQueryData<Task[]>(tasksQueryKey) ?? [];
       queryClient.setQueryData<Task[]>(tasksQueryKey, (prev) => {
         const list = prev ?? [];
         return list.map((t) =>
           t.id === vars.taskId ? { ...t, status: vars.status } : t,
         );
       });
       return { previous };
     },
     onError: (err, _vars, ctx) => {
       if (err instanceof ApiError && err.status === 401) {
         router.push("/login");
         return;
       }
       if (err instanceof ApiError && err.status === 409) {
         void queryClient.invalidateQueries({ queryKey: tasksQueryKey });
       }
       if (!ctx) return;
       queryClient.setQueryData<Task[]>(tasksQueryKey, ctx.previous);
       setUpdateMessage("Failed to update task.");
     },
     onSuccess: (serverTask) => {
       queryClient.setQueryData<Task[]>(tasksQueryKey, (prev) => {
         const list = prev ?? [];
         return list.map((t) => (t.id === serverTask.id ? serverTask : t));
       });
     },
   });

   const archive = useMutation({
     mutationFn: (taskId: string) => archiveTask(taskId),
     onMutate: async (taskId) => {
       setUpdateMessage(null);
       await queryClient.cancelQueries({ queryKey: tasksQueryKey });
       const previous = queryClient.getQueryData<Task[]>(tasksQueryKey) ?? [];
       queryClient.setQueryData<Task[]>(tasksQueryKey, (prev) => {
         const list = prev ?? [];
         return list.map((t) => (t.id === taskId ? { ...t, status: "archived" } : t));
       });
       return { previous };
     },
     onError: (err, _taskId, ctx) => {
       if (err instanceof ApiError && err.status === 401) {
         router.push("/login");
         return;
       }
       if (!ctx) return;
       queryClient.setQueryData<Task[]>(tasksQueryKey, ctx.previous);
       setUpdateMessage("Failed to archive task.");
     },
     onSuccess: (serverTask) => {
       queryClient.setQueryData<Task[]>(tasksQueryKey, (prev) => {
         const list = prev ?? [];
         return list.map((t) => (t.id === serverTask.id ? serverTask : t));
       });
     },
   });

   const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

   const visibleTasks = tasks.filter((t) => t.status !== "archived");

   return (
     <section className="mt-6">
       <div className="flex flex-wrap items-center justify-between gap-3">
         <div>
           <h2 className="text-lg font-semibold">Tasks</h2>
           <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
             {visibleTasks.length} active task(s).
           </p>
         </div>
         <Button type="button" onClick={() => setOpen(true)}>
           New task
         </Button>
       </div>

       {isLoading ? (
         <p className="mt-6 text-sm text-zinc-600 dark:text-zinc-400">
           Loading tasks…
         </p>
       ) : null}

       {updateMessage ? (
         <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">
           {updateMessage}
         </p>
       ) : null}

       {error && !isLoading ? (
         <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">
           Failed to load tasks.
         </p>
       ) : null}

       <div className="mt-6 space-y-4">
         {visibleTasks.map((task) => {
           const overdue =
             task.due_date != null && task.due_date < todayStr && task.status !== "done";

           const priorityVariant =
             task.priority === "urgent"
               ? ("destructive" as const)
               : ("secondary" as const);

           return (
             <article
               key={task.id}
               className="rounded-2xl border border-black/10 p-5 dark:border-white/10"
             >
               <div className="flex flex-wrap items-start justify-between gap-4">
                 <div className="min-w-[220px]">
                   <Link
                     href={`/tasks/${task.id}`}
                     className="text-base font-semibold hover:underline"
                   >
                     {task.title}
                   </Link>
                   {task.description ? (
                     <p className="mt-2 line-clamp-3 text-sm text-zinc-600 dark:text-zinc-400">
                       {task.description}
                     </p>
                   ) : null}

                   <div className="mt-3 flex flex-wrap gap-2">
                     <Badge variant={overdue ? "destructive" : "secondary"}>
                       {task.due_date ? `Due ${task.due_date}` : "No due date"}
                     </Badge>
                     <Badge variant={priorityVariant}>
                       Priority: {task.priority}
                     </Badge>
                     <Badge variant="default">Status: {task.status}</Badge>
                   </div>
                 </div>

                 <div className="space-y-3">
                   <div className="space-y-1">
                     <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                       Update status
                     </label>
                     <Select
                       value={task.status}
                       onValueChange={(v) => {
                         if (v === task.status) return;
                         void updateStatus.mutate({ taskId: task.id, status: v as TaskStatus });
                       }}
                     >
                       <option value="todo">To do</option>
                       <option value="in_progress">In progress</option>
                       <option value="done">Done</option>
                     </Select>
                   </div>

                   <div className="flex flex-wrap gap-2">
                     <Button
                       type="button"
                       variant="destructive"
                       onClick={() => void archive.mutate(task.id)}
                       disabled={archive.isPending || updateStatus.isPending}
                     >
                       Archive
                     </Button>
                   </div>
                 </div>
               </div>
             </article>
           );
         })}

         {visibleTasks.length === 0 && !isLoading ? (
           <div className="rounded-2xl border border-dashed border-black/15 p-8 dark:border-white/15">
             <p className="text-sm text-zinc-600 dark:text-zinc-400">No active tasks yet.</p>
           </div>
         ) : null}
       </div>

       <TaskForm
         projectId={projectId}
         open={open}
         onOpenChange={setOpen}
         tasksQueryKey={tasksQueryKey}
       />
     </section>
   );
 }

