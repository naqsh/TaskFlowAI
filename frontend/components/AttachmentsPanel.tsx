"use client";

import { useMemo } from "react";

import { getApiBase } from "@/lib/api";
import { useAttachments } from "@/hooks/useAttachments";
import type { Attachment } from "@/hooks/useAttachments";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

export function AttachmentsPanel({ taskId }: { taskId: string }) {
  const attachmentsQuery = useAttachments(taskId);
  const apiBase = getApiBase();

  const items = useMemo(() => attachmentsQuery.attachments.slice(0, 20), [attachmentsQuery.attachments]);

  return (
    <section className="rounded-2xl border border-black/10 p-4 dark:border-white/10">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-sm font-semibold">Attachments</h2>
      </div>

      <div className="mt-3">
        <label className="block text-xs font-medium text-zinc-600">Upload a file</label>
        <input
          className="mt-1 w-full text-sm"
          type="file"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            attachmentsQuery.upload.mutate(file);
            e.currentTarget.value = "";
          }}
        />
      </div>

      {attachmentsQuery.isLoading ? (
        <p className="mt-3 text-sm text-zinc-600">Loading attachments…</p>
      ) : items.length === 0 ? (
        <p className="mt-3 text-sm text-zinc-600">No attachments yet.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {items.map((a: Attachment) => (
            <li key={a.id} className="rounded-lg border border-black/10 p-2 dark:border-white/10">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{a.filename}</p>
                  <p className="mt-1 text-xs text-zinc-600">
                    {a.mime_type} · {formatBytes(a.size_bytes)}
                  </p>
                </div>
                <a
                  className="text-xs font-medium text-taskflow-primary hover:underline"
                  href={apiBase ? `${apiBase}${a.download_url}` : a.download_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}

      {attachmentsQuery.upload.isError ? (
        <p className="mt-3 text-xs text-red-600">Upload failed.</p>
      ) : null}
    </section>
  );
}

