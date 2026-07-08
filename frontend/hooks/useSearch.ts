"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchSearch, type SearchResponse } from "@/lib/search";

export function useSearch(params: { q: string; type?: "tasks" | "projects" | "comments" | "all" }) {
  return useQuery<SearchResponse>({
    queryKey: ["search", params.q, params.type ?? "tasks"],
    queryFn: () =>
      fetchSearch({
        q: params.q,
        type: params.type ?? "tasks",
        limit: 10,
        offset: 0,
      }),
    enabled: params.q.trim().length > 0,
  });
}

