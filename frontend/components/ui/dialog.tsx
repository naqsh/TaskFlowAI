 "use client";

 import React, { createContext, useContext } from "react";

 type DialogContextValue = {
   open: boolean;
   setOpen: (open: boolean) => void;
 };

 const DialogContext = createContext<DialogContextValue | null>(null);

 export function Dialog({
   open,
   onOpenChange,
   children,
 }: {
   open: boolean;
   onOpenChange: (open: boolean) => void;
   children: React.ReactNode;
 }) {
   return (
     <DialogContext.Provider
       value={{ open, setOpen: onOpenChange }}
     >
       {children}
     </DialogContext.Provider>
   );
 }

 export function DialogContent({
   children,
 }: {
   children: React.ReactNode;
 }) {
   const ctx = useContext(DialogContext);
   if (!ctx?.open) return null;

   return (
     <div
       className="fixed inset-0 z-50"
       role="dialog"
       aria-modal="true"
     >
       <div
         className="absolute inset-0 bg-black/30"
         onClick={() => ctx.setOpen(false)}
       />
       <div className="relative mx-auto mt-12 w-full max-w-lg rounded-2xl border border-black/10 bg-background p-6 shadow-lg">
         {children}
       </div>
     </div>
   );
 }

 export function DialogHeader({ children }: { children: React.ReactNode }) {
   return <div className="mb-4">{children}</div>;
 }

 export function DialogTitle({
   children,
 }: {
   children: React.ReactNode;
 }) {
   return <h3 className="text-lg font-semibold">{children}</h3>;
 }

 export function DialogDescription({
   children,
 }: {
   children: React.ReactNode;
 }) {
   return <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{children}</p>;
 }

