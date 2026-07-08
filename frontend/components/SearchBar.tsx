"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getAuthToken } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useSearch } from "@/hooks/useSearch";

export function SearchBar() {
  const router = useRouter();
  const authed = Boolean(getAuthToken());

  const [value, setValue] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");

  const qForSearch = authed ? submittedQ : "";
  const searchQuery = useSearch({
    q: qForSearch,
    type: "all",
  });

  const items = useMemo(() => searchQuery.data?.items ?? [], [searchQuery.data?.items]);

  return (
    <div className="relative w-72">
      <form
        className="flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmittedQ(value);
        }}
      >
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Search tasks, comments…"
          aria-label="Search"
        />
        <Button type="submit" size="icon" variant="secondary" aria-label="Search">
          S
        </Button>
      </form>

      {authed && submittedQ.trim().length > 0 ? (
        <div className="absolute left-0 top-full z-10 mt-2 w-full rounded-xl border border-black/10 bg-background p-3 shadow-lg dark:border-white/10">
          {searchQuery.isLoading ? (
            <p className="text-sm text-zinc-600">Searching…</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-zinc-600">No results.</p>
          ) : (
            <ul className="space-y-2">
              {items.slice(0, 6).map((it) => (
                <li key={`${it.kind}:${it.id}`}>
                  <button
                    type="button"
                    className="w-full rounded-lg p-2 text-left hover:bg-black/5 dark:hover:bg-white/5"
                    onClick={() => {
                      if (it.kind === "task") {
                        router.push(`/tasks/${it.id}`);
                      }
                    }}
                  >
                    <div className="text-xs font-medium text-zinc-600">{it.kind}</div>
                    <div className="mt-1 text-sm font-medium">{it.title ?? "Result"}</div>
                    {it.snippet ? (
                      <div className="mt-1 line-clamp-2 text-xs text-zinc-600">{it.snippet}</div>
                    ) : null}
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

