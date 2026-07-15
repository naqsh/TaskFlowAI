"""In-memory store for refactoring runs awaiting human approval."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from backend.refactoring.schemas import RefactorFinding, RefactorPlanStep, RunStatus


@dataclass
class RefactorRunState:
    run_id: str
    goal: str
    operation: str
    symbol: str | None
    new_name: str | None
    status: RunStatus
    plan: list[RefactorPlanStep]
    findings: list[RefactorFinding]
    trace_id: str
    approved_finding_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RefactorRunStore:
    """Process-local store (YOLO MVP — swap for Redis/DB later)."""

    def __init__(self) -> None:
        self._runs: dict[str, RefactorRunState] = {}
        self._lock = Lock()

    def save(self, run: RefactorRunState) -> None:
        with self._lock:
            self._runs[run.run_id] = run

    def get(self, run_id: str) -> RefactorRunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()


# Shared default for API + tests
_default_store = RefactorRunStore()


def get_run_store() -> RefactorRunStore:
    return _default_store
