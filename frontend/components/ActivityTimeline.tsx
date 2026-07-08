"use client";

import { useMemo } from "react";

import { useTaskActivity } from "@/hooks/useActivity";

function timeAgo(iso: string): string {
  const dt = new Date(iso);
  const diffMs = Date.now() - dt.getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ActivityTimeline({ taskId }: { taskId: string }) {
  const activityQuery = useTaskActivity(taskId);

  const items = useMemo(() => activityQuery.data?.items ?? [], [activityQuery.data?.items]);

  return (
    <aside className="rounded-2xl border border-black/10 p-4 dark:border-white/10">
      <h2 className="text-sm font-semibold">Activity</h2>
      {activityQuery.isLoading ? (
        <p className="mt-3 text-sm text-zinc-600">Loading activity…</p>
      ) : items.length === 0 ? (
        <p className="mt-3 text-sm text-zinc-600">No activity yet.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {items.map((e) => (
            <li key={e.id}>
              <p className="text-sm font-medium">{e.summary}</p>
              <p className="mt-1 text-xs text-zinc-600">{timeAgo(e.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

