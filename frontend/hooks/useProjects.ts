 "use client";

 import { useQuery } from "@tanstack/react-query";

 import { fetchProjects } from "@/lib/projects";

 export function useProjects(params: { limit?: number; offset?: number } = {}) {
   const limit = params.limit ?? 50;
   const offset = params.offset ?? 0;

   return useQuery({
     queryKey: ["projects", limit, offset],
     queryFn: () => fetchProjects(limit, offset),
   });
 }

