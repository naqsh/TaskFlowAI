"use client";

import Link from "next/link";

import { NotificationBell } from "@/components/NotificationBell";
import { SearchBar } from "@/components/SearchBar";

export function AppHeader() {
  return (
    <header className="border-b border-black/10 bg-background">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-3">
        <Link href="/" className="text-sm font-semibold text-taskflow-primary hover:underline">
          TaskFlow AI
        </Link>

        <div className="flex items-center gap-3">
          <SearchBar />
          <NotificationBell />
          <Link
            href="/preferences"
            className="rounded-lg border border-black/10 px-3 py-1.5 text-sm font-medium hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/5"
          >
            Preferences
          </Link>
        </div>
      </div>
    </header>
  );
}

