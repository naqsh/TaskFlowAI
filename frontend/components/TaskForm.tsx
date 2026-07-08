 "use client";

 import { zodResolver } from "@hookform/resolvers/zod";
 import { useMutation, useQueryClient } from "@tanstack/react-query";
 import { useRouter } from "next/navigation";
 import { useState } from "react";
 import { useForm } from "react-hook-form";
 import { z } from "zod";

 import { ApiError } from "@/lib/api";
 import { Input } from "@/components/ui/input";
 import { Button } from "@/components/ui/button";
 import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
 import { Select } from "@/components/ui/select";
 import { createTask, type Task, type TaskPriority } from "@/lib/tasks";
import type { AITaskDraft } from "@/lib/ai";
import { AITaskCreator } from "@/components/AITaskCreator";

 const EMPTY_UUID = "00000000-0000-0000-0000-000000000000";

 const taskCreateSchema = z.object({
   title: z.string().min(1, "Title is required").max(500),
   description: z
     .string()
     .max(10000, "Description is too long")
     .optional()
     .or(z.literal("")),
   priority: z.enum(["low", "medium", "high", "urgent"]),
   due_date: z.string().optional().or(z.literal("")),
 });

 type TaskCreateForm = z.infer<typeof taskCreateSchema>;

 function toOptionalText(v: string | undefined): string | null {
   if (!v) return null;
   const trimmed = v.trim();
   return trimmed ? trimmed : null;
 }

 function toOptionalDate(v: string | undefined): string | null {
   if (!v) return null;
   const trimmed = v.trim();
   return trimmed ? trimmed : null;
 }

 export function TaskForm({
   projectId,
   open,
   onOpenChange,
   tasksQueryKey,
 }: {
   projectId: string;
   open: boolean;
   onOpenChange: (open: boolean) => void;
   tasksQueryKey: readonly unknown[];
 }) {
   const queryClient = useQueryClient();
   const router = useRouter();

   const [submitError, setSubmitError] = useState<string | null>(null);
  const [aiOpen, setAiOpen] = useState(false);

   const form = useForm<TaskCreateForm>({
     resolver: zodResolver(taskCreateSchema),
     defaultValues: {
       title: "",
       description: "",
       priority: "medium",
       due_date: "",
     },
   });

   const createMutation = useMutation({
     mutationFn: (values: TaskCreateForm) =>
       createTask({
         project_id: projectId,
         title: values.title.trim(),
         description: toOptionalText(values.description),
         priority: values.priority as TaskPriority,
         due_date: toOptionalDate(values.due_date),
         assignee_id: null,
       }),
     onMutate: async (values: TaskCreateForm) => {
       await queryClient.cancelQueries({ queryKey: tasksQueryKey });
       const previous = queryClient.getQueryData<Task[]>(tasksQueryKey) ?? [];

       const tempId = crypto.randomUUID();
       const optimistic: Task = {
         id: tempId,
         workspace_id: EMPTY_UUID,
         project_id: projectId,
         title: values.title.trim(),
         description: toOptionalText(values.description),
         status: "todo",
         priority: values.priority,
         due_date: toOptionalDate(values.due_date),
         assignee_id: null,
         created_by: null,
         created_at: new Date().toISOString(),
         updated_at: new Date().toISOString(),
         warnings: [],
       };

       queryClient.setQueryData<Task[]>(tasksQueryKey, (prev) => [
         ...(prev ?? previous),
         optimistic,
       ]);

       return { previous, tempId };
     },
     onError: (err, _values, ctx) => {
       if (err instanceof ApiError && err.status === 401) {
         router.push("/login");
         return;
       }
       if (!ctx) return;
       queryClient.setQueryData<Task[]>(tasksQueryKey, ctx.previous);
       setSubmitError("Failed to create task.");
     },
     onSuccess: (serverTask, _values, ctx) => {
       if (!ctx) return;
       queryClient.setQueryData<Task[]>(tasksQueryKey, (prev) => {
         const list = prev ?? [];
         return list.map((t) => (t.id === ctx.tempId ? serverTask : t));
       });
     },
   });

   async function onSubmit(values: TaskCreateForm) {
     setSubmitError(null);
     createMutation.mutate(values, {
       onSuccess: () => {
         form.reset();
         onOpenChange(false);
       },
     });
   }

  function onApplyAIDraft(draft: AITaskDraft) {
    form.setValue("title", draft.title);
    form.setValue("priority", draft.priority);
    form.setValue("due_date", draft.due_date ?? "");
    setAiOpen(false);
  }

   return (
     <Dialog open={open} onOpenChange={onOpenChange}>
       <DialogContent>
         <DialogHeader>
           <DialogTitle>New task</DialogTitle>
           <DialogDescription>
             Create a task inside the selected project.
           </DialogDescription>
         </DialogHeader>

         <form
           onSubmit={form.handleSubmit(onSubmit)}
           className="space-y-4"
           noValidate
         >
           <div className="space-y-1">
             <label htmlFor="task-title" className="text-sm font-medium">
               Title
             </label>
             <Input id="task-title" {...form.register("title")} />
             {form.formState.errors.title ? (
               <p className="text-xs text-red-600">
                 {form.formState.errors.title.message}
               </p>
             ) : null}
           </div>

           <div className="space-y-1">
             <label htmlFor="task-description" className="text-sm font-medium">
               Description (optional)
             </label>
             <textarea
               id="task-description"
               className="w-full rounded-lg border border-black/15 bg-background p-3 text-sm outline-none focus-visible:border-taskflow-primary focus-visible:ring-2 focus-visible:ring-taskflow-primary/30"
               rows={4}
               {...form.register("description")}
             />
             {form.formState.errors.description ? (
               <p className="text-xs text-red-600">
                 {form.formState.errors.description.message}
               </p>
             ) : null}
           </div>

           <div className="grid gap-4 sm:grid-cols-2">
             <div className="space-y-1">
               <label htmlFor="task-priority" className="text-sm font-medium">
                 Priority
               </label>
               <Select
                 id="task-priority"
                 value={form.watch("priority")}
                 onValueChange={(v) => form.setValue("priority", v as TaskPriority)}
               >
                 <option value="low">Low</option>
                 <option value="medium">Medium</option>
                 <option value="high">High</option>
                 <option value="urgent">Urgent</option>
               </Select>
             </div>

             <div className="space-y-1">
               <label htmlFor="task-due-date" className="text-sm font-medium">
                 Due date (optional)
               </label>
               <Input
                 id="task-due-date"
                 type="date"
                 {...form.register("due_date")}
               />
             </div>
           </div>

           {submitError ? (
             <p role="alert" className="text-sm text-red-600 dark:text-red-400">
               {submitError}
             </p>
           ) : null}

           <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setAiOpen(true)}
              disabled={createMutation.isPending}
            >
              Create with AI
            </Button>
             <Button type="submit" disabled={createMutation.isPending}>
               {createMutation.isPending ? "Creating…" : "Create task"}
             </Button>
             <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
               Cancel
             </Button>
           </div>
         </form>
       </DialogContent>

      <AITaskCreator
        open={aiOpen}
        onOpenChange={setAiOpen}
        onApplyDraft={onApplyAIDraft}
      />
     </Dialog>
   );
 }

