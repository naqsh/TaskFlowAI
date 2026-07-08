"use client";

import { useRef, useState } from "react";
import { z } from "zod";

import type { AITaskDraft, AIResponse } from "@/lib/ai";
import { parseTaskWithAI } from "@/lib/ai";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ObservabilityBadge } from "@/components/ObservabilityBadge";
import { ConsentPromptModal } from "@/components/ConsentPromptModal";
import { taskPrioritySchema } from "@/lib/tasks";

const consentKey = "taskflow:aiConsentAccepted";

const aiDraftSchema = z.object({
  title: z.string().min(1),
  priority: taskPrioritySchema,
  due_date: z.string().nullable(),
});

export function AITaskCreator({
  open,
  onOpenChange,
  onApplyDraft,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApplyDraft: (draft: AITaskDraft) => void;
}) {
  const [nlInput, setNlInput] = useState<string>("");
  const [aiError, setAiError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [previewDraft, setPreviewDraft] = useState<AITaskDraft | null>(null);
  const [consentAccepted, setConsentAccepted] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return localStorage.getItem(consentKey) === "true";
    } catch {
      return false;
    }
  });
  const [consentModalOpen, setConsentModalOpen] = useState<boolean>(false);

  const pendingInputRef = useRef<string | null>(null);
  const canSubmit = nlInput.trim().length > 0 && !isLoading;

  async function runAI(input: string) {
    setAiError(null);
    setIsLoading(true);
    setPreviewDraft(null);
    try {
      const resp = await parseTaskWithAI(input);
      setResponse(resp);

      const draft = resp.data.task_draft;
      if (!draft) return;

      const parsedDraft = aiDraftSchema.parse({
        title: draft.title,
        priority: draft.priority,
        due_date: draft.due_date ?? null,
      });
      // Preview before save (TF-040) — do not auto-apply.
      setPreviewDraft(parsedDraft);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to run AI";
      setAiError(message);
    } finally {
      setIsLoading(false);
    }
  }

  function onGenerate() {
    const input = nlInput.trim();
    pendingInputRef.current = input;
    if (!consentAccepted) {
      setConsentModalOpen(true);
      return;
    }
    void runAI(input);
  }

  const applyConsent = () => {
    const input = pendingInputRef.current ?? nlInput.trim();
    setConsentAccepted(true);
    setConsentModalOpen(false);
    if (!input) return;
    void runAI(input);
  };

  const cancelConsent = () => {
    setConsentAccepted(false);
    setConsentModalOpen(false);
    pendingInputRef.current = null;
    setResponse(null);
    setPreviewDraft(null);
  };

  const confirmDraft = () => {
    if (!previewDraft) return;
    onApplyDraft(previewDraft);
    onOpenChange(false);
    setPreviewDraft(null);
    setResponse(null);
    setNlInput("");
  };

  return (
    <>
      <ConsentPromptModal
        open={consentModalOpen}
        onAccept={applyConsent}
        onDecline={cancelConsent}
      />

      <Dialog
        open={open}
        onOpenChange={(next) => {
          setAiError(null);
          setResponse(null);
          setPreviewDraft(null);
          onOpenChange(next);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create a task with AI</DialogTitle>
            <DialogDescription>
              Describe what you want to do. AI will generate a draft you can review.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <label className="text-sm font-medium" htmlFor="ai-task-input">
              What should we create?
            </label>
            <textarea
              id="ai-task-input"
              value={nlInput}
              onChange={(e) => setNlInput(e.target.value)}
              placeholder="e.g. Add a high-priority bug fix for login timeout due Friday"
              rows={5}
              className="w-full rounded-lg border border-black/15 bg-background p-3 text-sm outline-none focus-visible:border-taskflow-primary focus-visible:ring-2 focus-visible:ring-taskflow-primary/30"
            />

            {aiError ? (
              <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <span className="font-medium">AI error:</span> {aiError}
              </p>
            ) : null}

            {response ? (
              <div className="space-y-2">
                {response.status !== "success" ? (
                  <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    <span className="font-medium">Degraded AI response.</span> Status:{" "}
                    {response.status}. Review the draft carefully before saving.
                  </p>
                ) : null}

                {response.metadata ? <ObservabilityBadge metadata={response.metadata} /> : null}

                {previewDraft ? (
                  <div className="rounded-lg border border-black/10 p-3">
                    <p className="text-sm font-medium">Preview</p>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      Title: {previewDraft.title}
                    </p>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      Priority: {previewDraft.priority}
                    </p>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      Due: {previewDraft.due_date ?? "none"}
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="flex items-center justify-between gap-3 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <div className="flex gap-2">
              {previewDraft ? (
                <Button type="button" onClick={confirmDraft}>
                  Use draft
                </Button>
              ) : (
                <Button type="button" onClick={onGenerate} disabled={!canSubmit}>
                  {isLoading ? "Generating…" : "Generate draft"}
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
