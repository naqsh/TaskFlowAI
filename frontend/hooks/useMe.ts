 "use client";

 import { useQuery } from "@tanstack/react-query";

 import { fetchMe, type Me } from "@/lib/me";

 export function useMe() {
   return useQuery({
     queryKey: ["me"],
     queryFn: fetchMe,
   });
 }

 export type { Me };

