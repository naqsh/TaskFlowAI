 "use client";

 import Link from "next/link";
 import { useRouter } from "next/navigation";
 import { useEffect } from "react";

 import { ApiError } from "@/lib/api";
 import { Badge } from "@/components/ui/badge";
 import { CommentThread } from "@/components/CommentThread";
 import { useMe } from "@/hooks/useMe";
 import { useTask } from "@/hooks/useTask";

 export default function TaskPage({ params }: { params: { id: string } }) {
   const router = useRouter();

   const taskQuery = useTask(params.id);
   const meQuery = useMe();

   useEffect(() => {
     if (taskQuery.error instanceof ApiError && taskQuery.error.status === 401) {
       router.push("/login");
     }
   }, [taskQuery.error, router]);

   useEffect(() => {
     if (meQuery.error instanceof ApiError && meQuery.error.status === 401) {
       router.push("/login");
     }
   }, [meQuery.error, router]);

   const task = taskQuery.data;
   const me = meQuery.data;

   return (
     <main className="mx-auto w-full max-w-3xl px-6 py-10">
       <div className="mb-6 flex items-center justify-between gap-4">
         <Link href="/" className="text-sm font-medium text-taskflow-primary hover:underline">
           Back
         </Link>
         <Badge variant="secondary">{task ? `TF-010` : "TF-010"}</Badge>
       </div>

       {taskQuery.isLoading ? (
         <p className="text-sm text-zinc-600 dark:text-zinc-400">Loading task…</p>
       ) : null}

       {taskQuery.error ? (
         <p role="alert" className="text-sm text-red-600 dark:text-red-400">
           Failed to load task.
         </p>
       ) : null}

       {task ? (
         <section className="rounded-2xl border border-black/10 p-6 dark:border-white/10">
           <h1 className="text-2xl font-semibold">{task.title}</h1>
           {task.description ? (
             <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">{task.description}</p>
           ) : null}

           <div className="mt-4 flex flex-wrap gap-2">
             <Badge variant="default">Status: {task.status}</Badge>
             <Badge variant="secondary">Priority: {task.priority}</Badge>
             <Badge variant="secondary">
               Due: {task.due_date ? task.due_date : "—"}
             </Badge>
           </div>

           {task.warnings.length > 0 ? (
             <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100">
               {task.warnings.map((w) => (
                 <div key={w}>{w}</div>
               ))}
             </div>
           ) : null}
         </section>
       ) : null}

       {task ? (
         <div className="mt-8">
           <CommentThread taskId={task.id} currentUserId={me?.id ?? null} />
         </div>
       ) : null}
     </main>
   );
 }

