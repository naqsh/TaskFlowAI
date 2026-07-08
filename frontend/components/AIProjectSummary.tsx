"use client";

import { useState } from "react";

import type { AIResponse } from "@/lib/ai";
import { summarizeProjectWithAI } from "@/lib/ai";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ObservabilityBadge } from "@/components/ObservabilityBadge";

export function AIProjectSummary({ projectId }: { projectId: string }) {
  const [nlInput, setNlInput] = useState<string>("Summarize this project");
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function onSummarize() {
    setError(null);
    setIsLoading(true);
    try {
      const resp = await summarizeProjectWithAI(nlInput);
      setResponse(resp);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to run AI";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="mt-6 rounded-2xl border border-black/10 p-4 dark:border-white/10">
      <h2 className="text-lg font-semibold">AI project summary</h2>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
        Uses your description and workspace context to produce a short summary.
      </p>

      <div className="mt-3 space-y-2">
        <label className="text-sm font-medium" htmlFor={`ai-project-summary-${projectId}`}>
          Prompt
        </label>
        <Input
          id={`ai-project-summary-${projectId}`}
          value={nlInput}
          onChange={(e) => setNlInput(e.target.value)}
        />
      </div>

      <div className="mt-3 flex gap-3">
        <Button type="button" onClick={() => void onSummarize()} disabled={isLoading}>
          {isLoading ? "Summarizing…" : "Summarize"}
        </Button>
      </div>

      {error ? (
        <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      ) : null}

      {response?.data.summary ? (
        <div className="mt-4 space-y-2">
          <p className="whitespace-pre-wrap text-sm">{response.data.summary}</p>
          {response.metadata ? <ObservabilityBadge metadata={response.metadata} /> : null}
        </div>
      ) : null}
    </section>
  );
}

