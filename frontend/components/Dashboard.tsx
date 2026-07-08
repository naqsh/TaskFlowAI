 "use client";

 import { zodResolver } from "@hookform/resolvers/zod";
 import { useMutation, useQueryClient } from "@tanstack/react-query";
 import { useRouter } from "next/navigation";
 import { useMemo, useState } from "react";
 import { useForm } from "react-hook-form";
 import { z } from "zod";

 import { ApiError } from "@/lib/api";
 import { getApiBase } from "@/lib/api";
 import type { Project } from "@/lib/projects";
 import { createProject } from "@/lib/projects";
 import { useProjects } from "@/hooks/useProjects";
 import { useTasks } from "@/hooks/useTasks";
 import { Input } from "@/components/ui/input";
 import { Button } from "@/components/ui/button";
 import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
 import { Badge } from "@/components/ui/badge";
 import { ProjectCard } from "@/components/ProjectCard";

 const createProjectSchema = z.object({
   name: z.string().min(1, "Project name is required").max(200),
   description: z
     .string()
     .max(10000, "Description is too long")
     .optional()
     .or(z.literal("")),
 });

 type CreateProjectForm = z.infer<typeof createProjectSchema>;

 function toOptionalString(v: string | undefined): string | null {
   if (v == null) return null;
   const trimmed = v.trim();
   return trimmed ? trimmed : null;
 }

 export function Dashboard() {
   const apiBase = getApiBase();
   const router = useRouter();
   const queryClient = useQueryClient();

   const projectsQuery = useProjects({ limit: 50, offset: 0 });
   const tasksQuery = useTasks({ limit: 100, offset: 0 });

   const [open, setOpen] = useState(false);
   const [submitError, setSubmitError] = useState<string | null>(null);

   const overdueTasks = tasksQuery.data ?? [];
   const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

   const overdueByProject = useMemo(() => {
     const map = new Map<string, number>();
     for (const task of overdueTasks) {
       if (!task.due_date) continue;
       if (task.due_date >= todayStr) continue;
       if (task.status === "done" || task.status === "archived") continue;
       map.set(task.project_id, (map.get(task.project_id) ?? 0) + 1);
     }
     return map;
   }, [overdueTasks, todayStr]);

   const projects = projectsQuery.data ?? [];

   const createMutation = useMutation({
     mutationFn: (payload: { name: string; description?: string | null }) =>
       createProject(payload),
     onSuccess: () => {
       setOpen(false);
       setSubmitError(null);
       void queryClient.invalidateQueries({ queryKey: ["projects"] });
       void queryClient.invalidateQueries({ queryKey: ["tasks"] });
     },
     onError: (err) => {
       if (err instanceof ApiError && err.status === 401) {
         router.push("/login");
         return;
       }
       setSubmitError("Failed to create project.");
     },
   });

   const form = useForm<CreateProjectForm>({
     resolver: zodResolver(createProjectSchema),
     defaultValues: { name: "", description: "" },
   });

   async function onSubmit(values: CreateProjectForm) {
     setSubmitError(null);
     const payload = {
       name: values.name.trim(),
       description: toOptionalString(values.description),
     };
     createMutation.mutate(payload);
   }

   if (!apiBase) {
     return (
       <main className="mx-auto flex min-h-full w-full max-w-2xl flex-col gap-6 px-6 py-16">
         <div
           role="alert"
           className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
         >
           Set <code className="font-mono">NEXT_PUBLIC_API_URL</code> in{" "}
           <code className="font-mono">frontend/.env.local</code>.
         </div>
       </main>
     );
   }

   return (
     <main className="mx-auto w-full max-w-5xl px-6 py-10">
       <header className="flex flex-wrap items-end justify-between gap-4">
         <div>
           <p className="text-sm font-medium uppercase tracking-wide text-taskflow-primary">
             TaskFlow AI
           </p>
           <h1 className="mt-2 text-3xl font-semibold tracking-tight">Dashboard</h1>
           <p className="mt-2 max-w-xl text-sm text-zinc-600 dark:text-zinc-400">
             Manage projects and tasks scoped to your workspace.
           </p>
         </div>

         <div className="flex items-center gap-3">
           <Button type="button" onClick={() => setOpen(true)}>
             New project
           </Button>
           <Badge variant="secondary">{projects.length} projects</Badge>
         </div>
       </header>

       {projectsQuery.isLoading || tasksQuery.isLoading ? (
         <p className="mt-8 text-sm text-zinc-600 dark:text-zinc-400">Loading…</p>
       ) : null}

       {submitError ? (
         <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">
           {submitError}
         </p>
       ) : null}

       {projects.length === 0 && !projectsQuery.isLoading ? (
         <section className="mt-10 rounded-2xl border border-dashed border-black/15 p-8 dark:border-white/15">
           <h2 className="text-lg font-semibold">Get started</h2>
           <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
             Create your first project to start adding tasks.
           </p>
           <div className="mt-4">
             <Button type="button" onClick={() => setOpen(true)}>
               Create project
             </Button>
           </div>
         </section>
       ) : null}

       {projects.length > 0 ? (
         <section className="mt-8 grid gap-4 sm:grid-cols-2">
           {projects.map((project: Project) => (
             <ProjectCard
               key={project.id}
               project={project}
               overdueCount={overdueByProject.get(project.id) ?? 0}
             />
           ))}
         </section>
       ) : null}

       <Dialog open={open} onOpenChange={setOpen}>
         <DialogContent>
           <DialogHeader>
             <DialogTitle>Create project</DialogTitle>
             <DialogDescription>
               Add a project name and optional description.
             </DialogDescription>
           </DialogHeader>

           <form
             onSubmit={form.handleSubmit(onSubmit)}
             className="space-y-4"
             noValidate
           >
             <div className="space-y-1">
               <label htmlFor="project-name" className="text-sm font-medium">
                 Name
               </label>
               <Input
                 id="project-name"
                 placeholder="e.g. Marketing launch"
                 {...form.register("name")}
               />
               {form.formState.errors.name ? (
                 <p className="text-xs text-red-600">
                   {form.formState.errors.name.message}
                 </p>
               ) : null}
             </div>

             <div className="space-y-1">
               <label htmlFor="project-description" className="text-sm font-medium">
                 Description (optional)
               </label>
               <textarea
                 id="project-description"
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

             <div className="flex gap-3 pt-2">
               <Button type="submit" disabled={createMutation.isPending}>
                 {createMutation.isPending ? "Creating…" : "Create"}
               </Button>
               <Button
                 type="button"
                 variant="outline"
                 onClick={() => setOpen(false)}
               >
                 Cancel
               </Button>
             </div>
           </form>
         </DialogContent>
       </Dialog>
     </main>
   );
 }

