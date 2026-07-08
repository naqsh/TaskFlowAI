import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConsentPromptModal } from "@/components/ConsentPromptModal";
import { ObservabilityBadge } from "@/components/ObservabilityBadge";

describe("ConsentPromptModal", () => {
  it("calls onAccept when Accept is clicked", () => {
    const onAccept = vi.fn();
    const onDecline = vi.fn();
    render(<ConsentPromptModal open={true} onAccept={onAccept} onDecline={onDecline} />);
    fireEvent.click(screen.getByRole("button", { name: /accept/i }));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("calls onDecline when Decline is clicked", () => {
    const onAccept = vi.fn();
    const onDecline = vi.fn();
    render(<ConsentPromptModal open={true} onAccept={onAccept} onDecline={onDecline} />);
    fireEvent.click(screen.getByRole("button", { name: /decline/i }));
    expect(onDecline).toHaveBeenCalledTimes(1);
  });
});

describe("ObservabilityBadge", () => {
  it("renders model, tokens, and execution time", () => {
    render(
      <ObservabilityBadge
        metadata={{
          trace_id: "abc",
          execution_ms: 42,
          tokens_used: 120,
          model_used: "deterministic",
          prompt_version: "v2.0.0",
          agents_executed: ["planner_agent"],
          cache_hit_rate: 0.8,
          consensus_status: "agreement",
          reason: null,
        }}
      />,
    );
    expect(screen.getByText(/Model: deterministic/i)).toBeTruthy();
    expect(screen.getByText(/Tokens: 120/i)).toBeTruthy();
    expect(screen.getByText(/Time: 42ms/i)).toBeTruthy();
    expect(screen.getByText(/Cache: 80%/i)).toBeTruthy();
  });
});
