"""Refactoring agent nodes returning AgentResultEnvelope (ADR-004)."""

from __future__ import annotations

import time
from typing import Any, Literal
from uuid import uuid4

from backend.refactoring.patch import DeterministicPatchService, RenameRequest
from backend.refactoring.sandbox import SandboxError
from backend.refactoring.schemas import FeedbackDecision
from backend.refactoring.search import CodeSearchService
from backend.refactoring.verify import VerifyService
from backend.schemas.envelope import AgentResultEnvelope, EscalationPayload, ExecutionMetadata

_ = FeedbackDecision  # re-export convenience for callers/tests

AgentRunStatus = Literal["success", "escalated", "failed"]


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def search_agent_node(
    search: CodeSearchService,
    *,
    symbol: str,
    trace_id: str,
    started_ms: float,
) -> AgentResultEnvelope:
    hits = search.find_symbol(symbol)
    return AgentResultEnvelope(
        agent_id="refactoring.search",
        canonical_role="tool_operator",
        status="success",
        result={
            "symbol": symbol,
            "hit_count": len(hits),
            "hits": [
                {
                    "file_path": h.file_path,
                    "line": h.line,
                    "col": h.col,
                    "kind": h.kind,
                    "symbol": h.symbol,
                    "snippet": h.snippet,
                }
                for h in hits
            ],
        },
        metadata=ExecutionMetadata(
            execution_ms=_elapsed_ms(started_ms),
            tokens_used=0,
            trace_id=trace_id,
            data_classification="internal",
        ),
        escalation=EscalationPayload(),
    )


def report_agent_node(
    *,
    findings: list[dict[str, Any]],
    goal: str,
    trace_id: str,
    started_ms: float,
) -> AgentResultEnvelope:
    prioritized = sorted(
        findings,
        key=lambda f: {"high": 0, "medium": 1, "low": 2}.get(str(f.get("priority")), 9),
    )
    return AgentResultEnvelope(
        agent_id="refactoring.report",
        canonical_role="planner",
        status="success",
        result={"goal": goal, "finding_count": len(prioritized), "findings": prioritized},
        metadata=ExecutionMetadata(
            execution_ms=_elapsed_ms(started_ms),
            tokens_used=0,
            trace_id=trace_id,
            data_classification="internal",
        ),
        escalation=EscalationPayload(),
    )


def patch_agent_node(
    patcher: DeterministicPatchService,
    *,
    requests: list[RenameRequest],
    trace_id: str,
    started_ms: float,
) -> AgentResultEnvelope:
    changed: list[str] = []
    try:
        for req in requests:
            if patcher.rename_symbol(req):
                changed.append(req.file_path)
    except SandboxError as exc:
        return AgentResultEnvelope(
            agent_id="refactoring.patch",
            canonical_role="tool_operator",
            status="failed",
            result={"changed_files": changed, "error": str(exc)},
            metadata=ExecutionMetadata(
                execution_ms=_elapsed_ms(started_ms),
                tokens_used=0,
                trace_id=trace_id or str(uuid4()),
            ),
            escalation=EscalationPayload(
                reason="verification_failed",
                retry_allowed=True,
                context={"error": str(exc)},
            ),
        )

    return AgentResultEnvelope(
        agent_id="refactoring.patch",
        canonical_role="tool_operator",
        status="success",
        result={"changed_files": changed, "patched": len(changed)},
        metadata=ExecutionMetadata(
            execution_ms=_elapsed_ms(started_ms),
            tokens_used=0,
            trace_id=trace_id,
            data_classification="internal",
        ),
        escalation=EscalationPayload(),
    )


def verify_agent_node(
    verifier: VerifyService,
    *,
    relative_paths: list[str],
    trace_id: str,
    started_ms: float,
) -> AgentResultEnvelope:
    result = verifier.verify_files(relative_paths)
    status: AgentRunStatus = "success" if result.passed else "escalated"
    return AgentResultEnvelope(
        agent_id="refactoring.verify",
        canonical_role="verifier",
        status=status,
        result={
            "passed": result.passed,
            "outcome": result.outcome,
            "details": result.details,
            "files": relative_paths,
        },
        metadata=ExecutionMetadata(
            execution_ms=_elapsed_ms(started_ms),
            tokens_used=0,
            trace_id=trace_id,
            data_classification="internal",
        ),
        escalation=EscalationPayload(
            reason=None if result.passed else "verification_failed",
            retry_allowed=not result.passed,
            context=None if result.passed else {"details": result.details},
        ),
    )
