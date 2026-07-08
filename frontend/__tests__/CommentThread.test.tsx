import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommentThread, sanitizeCommentHtml } from "@/components/CommentThread";

vi.mock("@/lib/comments", () => ({
  fetchComments: vi.fn().mockResolvedValue([
    {
      id: "11111111-1111-4111-8111-111111111111",
      workspace_id: "22222222-2222-4222-8222-222222222222",
      task_id: "33333333-3333-4333-8333-333333333333",
      author_id: "44444444-4444-4444-8444-444444444444",
      body: '<p>Safe</p><script>alert("xss")</script>',
      created_at: "2026-07-08T12:00:00Z",
      updated_at: "2026-07-08T12:00:00Z",
    },
  ]),
  createComment: vi.fn(),
  updateComment: vi.fn(),
  deleteComment: vi.fn(),
}));

describe("sanitizeCommentHtml", () => {
  it("removes script tags from rendered HTML", () => {
    const dirty = '<p>Hello</p><script>alert(1)</script>';
    const clean = sanitizeCommentHtml(dirty);
    expect(clean).not.toContain("<script>");
    expect(clean).not.toContain("alert");
    expect(clean).toContain("Hello");
  });
});

describe("CommentThread", () => {
  it("renders sanitized comment bodies without script tags", async () => {
    render(
      <CommentThread
        taskId="33333333-3333-4333-8333-333333333333"
        currentUserId="44444444-4444-4444-8444-444444444444"
      />,
    );

    expect(await screen.findByText("Safe")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
});
