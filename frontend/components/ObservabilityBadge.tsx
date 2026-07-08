"use client";

import type { AIResponse } from "@/lib/ai";
import { Badge } from "@/components/ui/badge";

export function ObservabilityBadge({
  metadata,
}: {
  metadata: AIResponse["metadata"];
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge variant="secondary">Model: {metadata.model_used ?? "n/a"}</Badge>
      <Badge variant="secondary">Tokens: {metadata.tokens_used}</Badge>
      <Badge variant="secondary">Time: {metadata.execution_ms}ms</Badge>
      {metadata.cache_hit_rate != null ? (
        <Badge variant="secondary">Cache: {(metadata.cache_hit_rate * 100).toFixed(0)}%</Badge>
      ) : null}
      {metadata.consensus_status ? (
        <Badge variant="secondary">Consensus: {metadata.consensus_status}</Badge>
      ) : null}
    </div>
  );
}

