"""Agentic refactoring loop orchestration (ADR-004)."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from uuid import UUID

from backend.agents.refactoring.nodes import (
    patch_agent_node,
    report_agent_node,
    search_agent_node,
    verify_agent_node,
)
from backend.refactoring.feedback import FeedbackStore
from backend.refactoring.patch import DeterministicPatchService, RenameRequest
from backend.refactoring.sandbox import RefactoringSandbox, SandboxError
from backend.refactoring.schemas import (
    ApplyResult,
    FeedbackEvent,
    FindingPriority,
    RefactorFinding,
    RefactorPlanStep,
    RefactorRunReport,
)
from backend.refactoring.search import CodeSearchService
from backend.refactoring.snapshot import SnapshotService
from backend.refactoring.store import RefactorRunState, RefactorRunStore, get_run_store
from backend.refactoring.verify import VerifyService


class AgenticRefactoringService:
    """
    Cyclical pipeline:
    Goal → Plan → Read/Search → Report → Human approval → Snapshot → Patch → Verify → Loop/Rollback
    """

    def __init__(
        self,
        *,
        sandbox_root: str | Path,
        verify_command: str = "",
        feedback_path: str | Path = ".taskflow/refactoring-feedback.jsonl",
        run_store: RefactorRunStore | None = None,
    ) -> None:
        self._sandbox = RefactoringSandbox(sandbox_root)
        self._search = CodeSearchService(self._sandbox)
        self._snapshot = SnapshotService(self._sandbox)
        self._patch = DeterministicPatchService(self._sandbox)
        self._verify = VerifyService(self._sandbox, verify_command=verify_command)
        self._feedback = FeedbackStore(feedback_path)
        self._store = run_store or get_run_store()

    def analyze(
        self,
        *,
        goal: str,
        symbol: str,
        new_name: str | None = None,
        trace_id: str | None = None,
    ) -> RefactorRunReport:
        """Stages 1–5: Goal, Plan, Read/Search, Report (no mutation)."""
        started = time.perf_counter()
        tid = trace_id or str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        plan = [
            RefactorPlanStep(
                order=1,
                description="Search sandbox for symbol definitions and call sites",
            ),
            RefactorPlanStep(
                order=2,
                description="Prioritize findings; propose deterministic AST rename",
            ),
            RefactorPlanStep(order=3, description="Await human approval of finding IDs"),
            RefactorPlanStep(
                order=4,
                description="Snapshot -> Patch -> Verify -> Rollback on failure",
            ),
        ]

        search_env = search_agent_node(
            self._search,
            symbol=symbol,
            trace_id=tid,
            started_ms=started,
        )
        hits = search_env.result.get("hits", [])

        findings: list[RefactorFinding] = []
        for idx, hit in enumerate(hits):
            if not isinstance(hit, dict):
                continue
            file_path = str(hit.get("file_path", ""))
            kind = str(hit.get("kind", "name"))
            priority: FindingPriority = "high" if kind == "definition" else "medium"
            finding_id = f"{run_id}:{idx}"
            suggested = (
                f"Rename '{symbol}' → '{new_name}' via AST"
                if new_name
                else f"Review symbol '{symbol}' usage and rename for clarity"
            )
            findings.append(
                RefactorFinding(
                    finding_id=finding_id,
                    priority=priority,
                    kind="rename_symbol",
                    reason=(
                        f"{kind} of '{symbol}' at {file_path}:{hit.get('line')} — "
                        f"{hit.get('snippet', '')}"
                    ),
                    file_path=file_path,
                    symbol=symbol,
                    line=int(hit["line"]) if hit.get("line") is not None else None,
                    suggested_fix=suggested,
                    patch_payload={
                        "operation": "rename_symbol",
                        "old_name": symbol,
                        "new_name": new_name,
                        "file_path": file_path,
                    },
                )
            )

        # Deduplicate by file for patch application (still report per-hit).
        report_env = report_agent_node(
            findings=[f.model_dump() for f in findings],
            goal=goal,
            trace_id=tid,
            started_ms=started,
        )
        _ = report_env  # envelope retained for metrics/consistency

        run = RefactorRunState(
            run_id=run_id,
            goal=goal,
            operation="rename_symbol",
            symbol=symbol,
            new_name=new_name,
            status="awaiting_approval",
            plan=plan,
            findings=findings,
            trace_id=tid,
        )
        self._store.save(run)

        return RefactorRunReport(
            run_id=run_id,
            goal=goal,
            status="awaiting_approval",
            plan=plan,
            findings=findings,
            trace_id=tid,
        )

    def apply(
        self,
        *,
        run_id: str,
        approved_finding_ids: list[str],
        user_id: UUID | None = None,
        workspace_id: UUID | None = None,
    ) -> ApplyResult:
        """Stages 6–10: Human approval → Snapshot → Patch → Verify → Rollback."""
        run = self._store.get(run_id)
        if run is None:
            msg = f"Unknown refactoring run: {run_id}"
            raise SandboxError(msg)
        if not approved_finding_ids:
            msg = "Human approval required: approved_finding_ids must be non-empty"
            raise SandboxError(msg)

        approved = {fid for fid in approved_finding_ids}
        selected = [f for f in run.findings if f.finding_id in approved]
        unknown = approved - {f.finding_id for f in selected}
        if unknown:
            msg = f"Unknown finding IDs: {sorted(unknown)}"
            raise SandboxError(msg)

        # Record accept signals before mutation.
        for finding in selected:
            self._feedback.record(
                FeedbackEvent(
                    run_id=run_id,
                    finding_id=finding.finding_id,
                    decision="accepted",
                    user_id=user_id,
                    workspace_id=workspace_id,
                    trace_id=run.trace_id,
                )
            )

        # One rename patch per unique file (deterministic AST).
        files_to_patch: dict[str, RenameRequest] = {}
        for finding in selected:
            payload = finding.patch_payload
            old_name = str(payload.get("old_name") or run.symbol or "")
            new_name = payload.get("new_name") or run.new_name
            file_path = str(payload.get("file_path") or finding.file_path)
            if not old_name or not new_name:
                msg = "Rename requires old_name and new_name (provide new_name at analyze or apply)"
                raise SandboxError(msg)
            files_to_patch[file_path] = RenameRequest(
                old_name=old_name,
                new_name=str(new_name),
                file_path=file_path,
            )

        changed_files = list(files_to_patch.keys())
        snapshot = self._snapshot.capture(changed_files)
        run.status = "applying"
        run.approved_finding_ids = list(approved_finding_ids)
        self._store.save(run)

        started = time.perf_counter()
        try:
            patch_env = patch_agent_node(
                self._patch,
                requests=list(files_to_patch.values()),
                trace_id=run.trace_id,
                started_ms=started,
            )
            if patch_env.status != "success":
                self._snapshot.restore(snapshot)
                run.status = "rolled_back"
                self._store.save(run)
                return ApplyResult(
                    run_id=run_id,
                    status="rolled_back",
                    applied_finding_ids=list(approved_finding_ids),
                    changed_files=changed_files,
                    verify_outcome="fail",
                    rolled_back=True,
                    message=str(patch_env.escalation.context or patch_env.result),
                    trace_id=run.trace_id,
                )

            verify_env = verify_agent_node(
                self._verify,
                relative_paths=changed_files,
                trace_id=run.trace_id,
                started_ms=started,
            )
            verify_passed = bool(verify_env.result.get("passed"))

            if not verify_passed:
                self._snapshot.restore(snapshot)
                run.status = "rolled_back"
                self._store.save(run)
                self._feedback.record(
                    FeedbackEvent(
                        run_id=run_id,
                        finding_id=None,
                        decision="accepted",
                        verify_outcome="fail",
                        notes=str(verify_env.result.get("details")),
                        user_id=user_id,
                        workspace_id=workspace_id,
                        trace_id=run.trace_id,
                    )
                )
                return ApplyResult(
                    run_id=run_id,
                    status="rolled_back",
                    applied_finding_ids=list(approved_finding_ids),
                    changed_files=changed_files,
                    verify_outcome="fail",
                    rolled_back=True,
                    message=str(verify_env.result.get("details", "verification failed")),
                    trace_id=run.trace_id,
                )

            run.status = "verified"
            self._store.save(run)
            self._feedback.record(
                FeedbackEvent(
                    run_id=run_id,
                    finding_id=None,
                    decision="accepted",
                    verify_outcome="pass",
                    user_id=user_id,
                    workspace_id=workspace_id,
                    trace_id=run.trace_id,
                )
            )
            return ApplyResult(
                run_id=run_id,
                status="verified",
                applied_finding_ids=list(approved_finding_ids),
                changed_files=changed_files,
                verify_outcome="pass",
                rolled_back=False,
                message="Patches applied and verified",
                trace_id=run.trace_id,
            )
        finally:
            self._snapshot.cleanup(snapshot)

    def reject_findings(
        self,
        *,
        run_id: str,
        finding_ids: list[str],
        user_id: UUID | None = None,
        workspace_id: UUID | None = None,
        notes: str | None = None,
    ) -> int:
        """Record rejected findings as RL training signal (no mutation)."""
        run = self._store.get(run_id)
        if run is None:
            msg = f"Unknown refactoring run: {run_id}"
            raise SandboxError(msg)
        count = 0
        known = {f.finding_id for f in run.findings}
        for fid in finding_ids:
            if fid not in known:
                continue
            self._feedback.record(
                FeedbackEvent(
                    run_id=run_id,
                    finding_id=fid,
                    decision="rejected",
                    notes=notes,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    trace_id=run.trace_id,
                )
            )
            count += 1
        return count

    def get_report(self, run_id: str) -> RefactorRunReport:
        run = self._store.get(run_id)
        if run is None:
            msg = f"Unknown refactoring run: {run_id}"
            raise SandboxError(msg)
        return RefactorRunReport(
            run_id=run.run_id,
            goal=run.goal,
            status=run.status,
            plan=run.plan,
            findings=run.findings,
            trace_id=run.trace_id,
        )
