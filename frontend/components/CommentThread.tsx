"use client";

import DOMPurify from "dompurify";
import { useCallback, useEffect, useState } from "react";

import {
  createComment,
  deleteComment,
  fetchComments,
  updateComment,
  type Comment,
} from "@/lib/comments";

const SAFE_HTML_CONFIG = {
  ALLOWED_TAGS: ["p", "br", "strong", "em", "code"],
  ALLOWED_ATTR: [],
};

export function sanitizeCommentHtml(html: string): string {
  return DOMPurify.sanitize(html, SAFE_HTML_CONFIG);
}

type CommentThreadProps = {
  taskId: string;
  currentUserId?: string | null;
};

export function CommentThread({ taskId, currentUserId }: CommentThreadProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadComments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchComments(taskId);
      setComments(items);
    } catch {
      setError("Failed to load comments.");
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void loadComments();
  }, [loadComments]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) {
      return;
    }
    setError(null);
    try {
      const created = await createComment(taskId, draft.trim());
      setComments((prev) => [...prev, created]);
      setDraft("");
    } catch {
      setError("Failed to post comment.");
    }
  }

  async function handleSaveEdit(commentId: string) {
    if (!editDraft.trim()) {
      return;
    }
    setError(null);
    try {
      const updated = await updateComment(commentId, editDraft.trim());
      setComments((prev) => prev.map((c) => (c.id === commentId ? updated : c)));
      setEditingId(null);
      setEditDraft("");
    } catch {
      setError("Failed to update comment.");
    }
  }

  async function handleDelete(commentId: string) {
    setError(null);
    try {
      await deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch {
      setError("Failed to delete comment.");
    }
  }

  function canEdit(comment: Comment): boolean {
    return currentUserId != null && comment.author_id === currentUserId;
  }

  return (
    <section aria-label="Comment thread" className="space-y-4">
      <h2 className="text-lg font-semibold">Comments</h2>

      {loading ? <p className="text-sm text-zinc-500">Loading comments…</p> : null}
      {error ? (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      ) : null}

      <ul className="space-y-3">
        {comments.map((comment) => (
          <li
            key={comment.id}
            className="rounded-xl border border-black/10 p-4 dark:border-white/10"
          >
            {editingId === comment.id ? (
              <div className="space-y-2">
                <textarea
                  className="w-full rounded-lg border border-black/10 bg-transparent p-2 text-sm dark:border-white/15"
                  value={editDraft}
                  onChange={(e) => setEditDraft(e.target.value)}
                  rows={3}
                  aria-label="Edit comment"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded-lg bg-taskflow-primary px-3 py-1 text-sm text-white"
                    onClick={() => void handleSaveEdit(comment.id)}
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border px-3 py-1 text-sm"
                    onClick={() => {
                      setEditingId(null);
                      setEditDraft("");
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div
                  className="prose prose-sm dark:prose-invert max-w-none text-sm"
                  dangerouslySetInnerHTML={{
                    __html: sanitizeCommentHtml(comment.body),
                  }}
                />
                {canEdit(comment) ? (
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="text-xs text-taskflow-primary hover:underline"
                      onClick={() => {
                        setEditingId(comment.id);
                        setEditDraft(comment.body);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="text-xs text-red-600 hover:underline dark:text-red-400"
                      onClick={() => void handleDelete(comment.id)}
                    >
                      Delete
                    </button>
                  </div>
                ) : null}
              </>
            )}
          </li>
        ))}
      </ul>

      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-2">
        <label htmlFor="comment-body" className="sr-only">
          Add a comment
        </label>
        <textarea
          id="comment-body"
          className="w-full rounded-lg border border-black/10 bg-transparent p-3 text-sm dark:border-white/15"
          placeholder="Write a comment…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
        />
        <button
          type="submit"
          className="rounded-lg bg-taskflow-primary px-4 py-2 text-sm font-medium text-white hover:bg-taskflow-primary/90"
        >
          Post comment
        </button>
      </form>
    </section>
  );
}
