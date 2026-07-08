"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchProjectActivity, fetchTaskActivity, type ActivityListResponse } from "@/lib/activity";

export function useTaskActivity(taskId: string | undefined) {
  return useQuery<ActivityListResponse>({
    queryKey: ["activity", "task", taskId],
    queryFn: () =>
      fetchTaskActivity(taskId!, { limit: 50, offset: 0 }),
    enabled: Boolean(taskId),
  });
}

export function useProjectActivity(projectId: string | undefined) {
  return useQuery<ActivityListResponse>({
    queryKey: ["activity", "project", projectId],
    queryFn: () => fetchProjectActivity(projectId!, { limit: 50, offset: 0 }),
    enabled: Boolean(projectId),
  });
}

