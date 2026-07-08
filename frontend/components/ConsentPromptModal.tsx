"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function ConsentPromptModal({
  open,
  onAccept,
  onDecline,
}: {
  open: boolean;
  onAccept: () => void;
  onDecline: () => void;
}) {
  const storageKey = "taskflow:aiConsentAccepted";

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onDecline();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Allow AI assistance</DialogTitle>
          <DialogDescription>
            TaskFlow AI will use your input to generate a draft task/summary and may read existing
            workspace context for better results.
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              try {
                localStorage.setItem(storageKey, "false");
              } catch {
                // ignore storage errors
              }
              onDecline();
            }}
          >
            Decline
          </Button>
          <Button
            type="button"
            onClick={() => {
              try {
                localStorage.setItem(storageKey, "true");
              } catch {
                // ignore storage errors
              }
              onAccept();
            }}
          >
            Accept
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

