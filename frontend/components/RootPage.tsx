 "use client";

import { useState } from "react";

 import { isAuthenticated } from "@/lib/auth";

 import { Dashboard } from "./Dashboard";
 import { DashboardShell } from "./DashboardShell";

 export default function RootPage() {
  const [authed] = useState<boolean>(() => isAuthenticated());

   if (!authed) {
     return <DashboardShell />;
   }

   return <Dashboard />;
 }

