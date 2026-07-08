"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchTaskAttachments,
  type Attachment,
  type AttachmentListResponse,
  uploadTaskAttachment,
} from "@/lib/attachments";

export function useAttachments(taskId: string | undefined) {
  const queryClient = useQueryClient();

  const list = useQuery<AttachmentListResponse>({
    queryKey: ["attachments", taskId],
    queryFn: () => fetchTaskAttachments(taskId!, { limit: 20, offset: 0 }),
    enabled: Boolean(taskId),
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadTaskAttachment(taskId!, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["attachments", taskId] });
    },
  });

  return {
    attachments: list.data?.items ?? [],
    isLoading: list.isLoading,
    error: list.error,
    upload,
  };
}

export type { Attachment };

