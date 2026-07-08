from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionMetric:
    agent_id: str
    duration_ms: int
    tokens: int


class SecurityMonitor:
    """Record agent execution metrics (Part 1 scaffold)."""

    def __init__(self) -> None:
        self._count: int = 0
        self._last: ExecutionMetric | None = None

    def record_execution(self, agent_id: str, duration_ms: int, tokens: int) -> None:
        self._count += 1
        self._last = ExecutionMetric(agent_id=agent_id, duration_ms=duration_ms, tokens=tokens)

    @property
    def count(self) -> int:
        return self._count

    @property
    def last(self) -> ExecutionMetric | None:
        return self._last
