 "use client";

 import React from "react";

 import { cn } from "@/lib/utils";

 export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
   variant?: "default" | "secondary" | "destructive";
 };

 export function Badge({
   className,
   variant = "default",
   ...props
 }: BadgeProps) {
   return (
     <span
       className={cn(
         "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
         variant === "default" && "border-black/10 bg-black/5 text-zinc-700 dark:border-white/15",
         variant === "secondary" &&
           "border-black/10 bg-background text-zinc-700 dark:border-white/15",
         variant === "destructive" &&
           "border-destructive/30 bg-destructive/10 text-destructive dark:border-destructive/40",
         className,
       )}
       {...props}
     />
   );
 }

