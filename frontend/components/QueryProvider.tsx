 "use client";

 import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
 import React from "react";

 const queryClientSingleton = new QueryClient({
   defaultOptions: {
     queries: {
       staleTime: 15_000,
       retry: 1,
     },
     mutations: {
       retry: 0,
     },
   },
 });

 export function QueryProvider({ children }: { children: React.ReactNode }) {
   return (
     <QueryClientProvider client={queryClientSingleton}>
       {children}
     </QueryClientProvider>
   );
 }

