 "use client";

 import Link from "next/link";
 import { useRouter } from "next/navigation";
 import { useEffect } from "react";
 import { useQuery } from "@tanstack/react-query";

 import { ApiError } from "@/lib/api";
 import { fetchProject } from "@/lib/projects";
 import { Badge } from "@/components/ui/badge";
 import { TaskList } from "@/components/TaskList";

 export default function ProjectPage({ params }: { params: { id: string } }) {
   const router = useRouter();

   const projectQuery = useQuery({
     queryKey: ["project", params.id],
     queryFn: () => fetchProject(params.id),
     enabled: Boolean(params.id),
   });

   useEffect(() => {
     const err = projectQuery.error;
     if (!err) return;
     if (err instanceof ApiError && err.status === 401) router.push("/login");
   }, [projectQuery.error, router]);

   const project = projectQuery.data;

   return (
     <main className="mx-auto w-full max-w-5xl px-6 py-10">
       <div className="flex flex-wrap items-center justify-between gap-4">
         <div>
           <Link href="/" className="text-sm font-medium text-taskflow-primary hover:underline">
             Back to dashboard
           </Link>
           {projectQuery.isLoading ? (
             <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">Loading project…</p>
           ) : project ? (
             <>
               <h1 className="mt-3 text-2xl font-semibold">{project.name}</h1>
               {project.description ? (
                 <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{project.description}</p>
               ) : null}
               <div className="mt-3 flex flex-wrap gap-2">
                 <Badge variant="secondary">Workspace-scoped</Badge>
               </div>
             </>
           ) : null}
         </div>
       </div>

       <TaskList projectId={params.id} />
     </main>
   );
 }

