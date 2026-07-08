 "use client";

 import { cn } from "@/lib/utils";
 import React from "react";

 export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

 export function Input({ className, ...props }: InputProps) {
   return (
     <input
       className={cn(
         "h-10 w-full rounded-lg border border-black/15 bg-background px-3 text-sm outline-none placeholder:text-zinc-500 focus-visible:border-taskflow-primary focus-visible:ring-2 focus-visible:ring-taskflow-primary/30 dark:border-white/15 dark:placeholder:text-zinc-400",
         className,
       )}
       {...props}
     />
   );
 }

