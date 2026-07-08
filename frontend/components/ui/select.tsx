 "use client";

 import React from "react";

 import { cn } from "@/lib/utils";

 export type SelectProps = Omit<
   React.SelectHTMLAttributes<HTMLSelectElement>,
   "value" | "onChange"
 > & {
   value: string;
   onValueChange: (value: string) => void;
 };

 export function Select({
   className,
   value,
   onValueChange,
   children,
   ...props
 }: SelectProps) {
   return (
     <select
       className={cn(
         "h-10 w-full rounded-lg border border-black/15 bg-background px-3 text-sm outline-none focus-visible:border-taskflow-primary focus-visible:ring-2 focus-visible:ring-taskflow-primary/30 dark:border-white/15",
         className,
       )}
       value={value}
       onChange={(e) => onValueChange(e.target.value)}
       {...props}
     >
       {children}
     </select>
   );
 }

