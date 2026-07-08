"use client";

import { useMemo, useState } from "react";

import { getAuthToken } from "@/lib/api";
import { useNotifications } from "@/hooks/useNotifications";
import type { Notification } from "@/hooks/useNotifications";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const authed = Boolean(getAuthToken());

  const { notifications, totalUnread, markOne, markAll, isLoading } = useNotifications({
    limit: 10,
    offset: 0,
    enabled: authed,
  });

  const items = useMemo(() => notifications.slice(0, 10), [notifications]);

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        Notifications
        <Badge className="ml-2" variant="secondary">
          {totalUnread}
        </Badge>
      </Button>

      {open ? (
        <div className="absolute right-0 z-10 mt-2 w-80 rounded-xl border border-black/10 bg-background p-3 shadow-lg dark:border-white/10">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">Inbox</p>
            <button
              className="text-xs text-zinc-600 hover:underline"
              type="button"
              disabled={isLoading || totalUnread === 0}
              onClick={() => markAll.mutate()}
            >
              Mark all read
            </button>
          </div>

          {isLoading ? (
            <p className="mt-3 text-sm text-zinc-600">Loading…</p>
          ) : items.length === 0 ? (
            <p className="mt-3 text-sm text-zinc-600">No new notifications.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {items.map((n: Notification) => (
                <li key={n.id}>
                  <button
                    type="button"
                    className="w-full rounded-lg p-2 text-left hover:bg-black/5 dark:hover:bg-white/5"
                    onClick={() => {
                      markOne.mutate(n.id);
                      setOpen(false);
                    }}
                  >
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-zinc-600">{n.body}</p>
                    <p className="mt-1 text-[11px] text-zinc-500">{timeAgo(n.created_at)}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

