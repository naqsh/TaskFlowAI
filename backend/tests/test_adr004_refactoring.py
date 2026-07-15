"""ADR-004 agentic refactoring loop tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.refactoring.feedback import FeedbackStore
from backend.refactoring.patch import DeterministicPatchService, RenameRequest
from backend.refactoring.sandbox import RefactoringSandbox, SandboxError
from backend.refactoring.schemas import FeedbackEvent
from backend.refactoring.search import CodeSearchService
from backend.refactoring.service import AgenticRefactoringService
from backend.refactoring.snapshot import SnapshotService
from backend.refactoring.store import RefactorRunStore
from backend.refactoring.verify import VerifyService


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def sandbox_root(tmp_path: Path) -> Path:
    pkg = tmp_path / "sample"
    _write(
        pkg / "mod.py",
        "def temp2(x):\n    return x + 1\n\ndef caller():\n    return temp2(3)\n",
    )
    _write(pkg / "other.py", "from sample.mod import temp2\n\nVALUE = temp2(1)\n")
    return tmp_path


def test_sandbox_blocks_traversal(sandbox_root: Path) -> None:
    sandbox = RefactoringSandbox(sandbox_root)
    with pytest.raises(SandboxError):
        sandbox.resolve("../outside.py")


def test_search_finds_definitions_and_calls(sandbox_root: Path) -> None:
    search = CodeSearchService(RefactoringSandbox(sandbox_root))
    hits = search.find_symbol("temp2")
    kinds = {h.kind for h in hits}
    assert "definition" in kinds
    assert hits


def test_snapshot_restore_roundtrip(sandbox_root: Path) -> None:
    sandbox = RefactoringSandbox(sandbox_root)
    snap = SnapshotService(sandbox)
    rel = "sample/mod.py"
    original = (sandbox_root / rel).read_text(encoding="utf-8")
    snapshot = snap.capture([rel])
    (sandbox_root / rel).write_text("broken", encoding="utf-8")
    restored = snap.restore(snapshot)
    assert restored == [rel]
    assert (sandbox_root / rel).read_text(encoding="utf-8") == original
    snap.cleanup(snapshot)


def test_deterministic_rename_via_ast(sandbox_root: Path) -> None:
    sandbox = RefactoringSandbox(sandbox_root)
    patcher = DeterministicPatchService(sandbox)
    assert patcher.rename_symbol(
        RenameRequest(old_name="temp2", new_name="customer_state", file_path="sample/mod.py")
    )
    text = (sandbox_root / "sample" / "mod.py").read_text(encoding="utf-8")
    assert "customer_state" in text
    assert "temp2" not in text


def test_verify_fails_on_syntax_error(sandbox_root: Path) -> None:
    sandbox = RefactoringSandbox(sandbox_root)
    bad = sandbox_root / "sample" / "bad.py"
    _write(bad, "def oops(:\n    pass\n")
    result = VerifyService(sandbox).verify_files(["sample/bad.py"])
    assert result.passed is False
    assert result.outcome == "fail"


def test_analyze_requires_human_approval_before_mutation(
    sandbox_root: Path, tmp_path: Path
) -> None:
    store = RefactorRunStore()
    service = AgenticRefactoringService(
        sandbox_root=sandbox_root,
        feedback_path=tmp_path / "feedback.jsonl",
        run_store=store,
    )
    report = service.analyze(
        goal="Rename unclear identifier temp2 to customer_state",
        symbol="temp2",
        new_name="customer_state",
        trace_id="trace-test",
    )
    assert report.status == "awaiting_approval"
    assert report.findings
    # File unchanged until apply
    assert "def temp2" in (sandbox_root / "sample" / "mod.py").read_text(encoding="utf-8")


def test_apply_snapshot_patch_verify_success(sandbox_root: Path, tmp_path: Path) -> None:
    store = RefactorRunStore()
    feedback_path = tmp_path / "feedback.jsonl"
    service = AgenticRefactoringService(
        sandbox_root=sandbox_root,
        feedback_path=feedback_path,
        run_store=store,
    )
    report = service.analyze(
        goal="Rename temp2",
        symbol="temp2",
        new_name="customer_state",
    )
    ids = [f.finding_id for f in report.findings]
    result = service.apply(run_id=report.run_id, approved_finding_ids=ids)
    assert result.status == "verified"
    assert result.rolled_back is False
    assert "customer_state" in (sandbox_root / "sample" / "mod.py").read_text(encoding="utf-8")
    events = FeedbackStore(feedback_path).read_all()
    assert any(e.decision == "accepted" for e in events)
    assert any(e.verify_outcome == "pass" for e in events)


def test_apply_rolls_back_when_verify_fails(sandbox_root: Path, tmp_path: Path) -> None:
    store = RefactorRunStore()
    service = AgenticRefactoringService(
        sandbox_root=sandbox_root,
        # Force verify failure after patch
        verify_command='python -c "raise SystemExit(1)"',
        feedback_path=tmp_path / "feedback.jsonl",
        run_store=store,
    )
    report = service.analyze(
        goal="Rename temp2",
        symbol="temp2",
        new_name="customer_state",
    )
    original = (sandbox_root / "sample" / "mod.py").read_text(encoding="utf-8")
    ids = [f.finding_id for f in report.findings if f.file_path.endswith("mod.py")]
    result = service.apply(run_id=report.run_id, approved_finding_ids=ids)
    assert result.status == "rolled_back"
    assert result.rolled_back is True
    assert (sandbox_root / "sample" / "mod.py").read_text(encoding="utf-8") == original


def test_reject_findings_writes_feedback(sandbox_root: Path, tmp_path: Path) -> None:
    store = RefactorRunStore()
    feedback_path = tmp_path / "feedback.jsonl"
    service = AgenticRefactoringService(
        sandbox_root=sandbox_root,
        feedback_path=feedback_path,
        run_store=store,
    )
    report = service.analyze(goal="x", symbol="temp2", new_name="y")
    count = service.reject_findings(
        run_id=report.run_id,
        finding_ids=[report.findings[0].finding_id],
        notes="looks load-bearing",
    )
    assert count == 1
    events = FeedbackStore(feedback_path).read_all()
    assert events[0].decision == "rejected"


def test_apply_without_approval_ids_rejected(sandbox_root: Path, tmp_path: Path) -> None:
    store = RefactorRunStore()
    service = AgenticRefactoringService(
        sandbox_root=sandbox_root,
        feedback_path=tmp_path / "feedback.jsonl",
        run_store=store,
    )
    report = service.analyze(goal="x", symbol="temp2", new_name="y")
    with pytest.raises(SandboxError):
        service.apply(run_id=report.run_id, approved_finding_ids=[])


def test_feedback_event_schema_roundtrip() -> None:
    event = FeedbackEvent(
        run_id="r1",
        finding_id="f1",
        decision="accepted",
        verify_outcome="pass",
        trace_id="t1",
    )
    assert event.model_dump()["decision"] == "accepted"
