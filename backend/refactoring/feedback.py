"""Reinforcement-learning style feedback log (ADR-004)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from backend.refactoring.schemas import FeedbackEvent


class FeedbackStore:
    """Append-only JSONL store for accept/reject and verify outcomes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = Lock()

    def record(self, event: FeedbackEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = event.model_dump_json() + "\n"
        with self._lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def read_all(self) -> list[FeedbackEvent]:
        if not self._path.exists():
            return []
        events: list[FeedbackEvent] = []
        with self._path.open(encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                events.append(FeedbackEvent.model_validate(json.loads(raw)))
        return events
