from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from backend.logging_config import get_logger
from backend.metrics import (
    BLAST_RADIUS_SCORE,
    CONSENSUS_DISAGREEMENT_TOTAL,
    SECURITY_DWELL_TIME_SECONDS,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExecutionMetric:
    agent_id: str
    duration_ms: int
    tokens: int
    tool_calls: int = 0


@dataclass
class _IncidentState:
    incident_type: str
    started_at: float
    detected: bool = False
    detected_at: float | None = None


@dataclass
class _ToolBaseline:
    sizes: deque[int] = field(default_factory=lambda: deque(maxlen=50))
    latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=50))


class SecurityMonitor:
    """Security monitor: blast radius, dwell time, MCP baselines (TF-044/TF-045)."""

    def __init__(self, *, enabled: bool = True, max_score: int = 100) -> None:
        self._enabled = enabled
        self._max_score = max_score
        self._count: int = 0
        self._last: ExecutionMetric | None = None
        self._tool_calls: dict[str, int] = defaultdict(int)
        self._escalations: dict[str, int] = defaultdict(int)
        self._baselines: dict[str, _ToolBaseline] = defaultdict(_ToolBaseline)
        self._incidents: dict[str, _IncidentState] = {}
        self._anomaly_flags: list[str] = []

    @property
    def count(self) -> int:
        return self._count

    @property
    def last(self) -> ExecutionMetric | None:
        return self._last

    @property
    def anomaly_flags(self) -> list[str]:
        return list(self._anomaly_flags)

    def record_execution(
        self,
        agent_id: str,
        duration_ms: int,
        tokens: int,
        *,
        tool_calls: int = 0,
    ) -> None:
        if not self._enabled:
            return
        self._count += 1
        self._tool_calls[agent_id] += tool_calls
        self._last = ExecutionMetric(
            agent_id=agent_id,
            duration_ms=duration_ms,
            tokens=tokens,
            tool_calls=tool_calls,
        )
        score = self._compute_blast_radius(agent_id)
        BLAST_RADIUS_SCORE.labels(agent_id=agent_id).set(score)

    def record_escalation(self, agent_id: str) -> None:
        if not self._enabled:
            return
        self._escalations[agent_id] += 1
        CONSENSUS_DISAGREEMENT_TOTAL.inc()
        score = self._compute_blast_radius(agent_id)
        BLAST_RADIUS_SCORE.labels(agent_id=agent_id).set(score)

    def record_mcp_response(
        self,
        tool: str,
        *,
        response_size: int,
        latency_ms: float,
        default_size_threshold: int = 50_000,
        default_sigma: float = 2.0,
    ) -> bool:
        """Record MCP response metrics; return True if anomaly detected."""
        if not self._enabled:
            return False

        baseline = self._baselines[tool]
        anomaly = False

        if not baseline.sizes:
            if response_size > default_size_threshold:
                anomaly = True
                self._anomaly_flags.append(f"mcp_size_anomaly:{tool}")
        else:
            mean = sum(baseline.sizes) / len(baseline.sizes)
            variance = sum((x - mean) ** 2 for x in baseline.sizes) / len(baseline.sizes)
            std = math.sqrt(variance) if variance > 0 else 1.0
            if response_size > mean + default_sigma * std:
                anomaly = True
                self._anomaly_flags.append(f"mcp_size_anomaly:{tool}")

        baseline.sizes.append(response_size)
        baseline.latencies_ms.append(latency_ms)
        return anomaly

    def record_incident_start(self, incident_id: str, incident_type: str) -> None:
        if incident_id in self._incidents:
            return
        self._incidents[incident_id] = _IncidentState(
            incident_type=incident_type,
            started_at=time.monotonic(),
        )

    def record_incident_detected(self, incident_id: str) -> float | None:
        incident = self._incidents.get(incident_id)
        if incident is None:
            logger.warning("dwell_time_missing_incident_start", incident_id=incident_id)
            return None
        if incident.detected:
            return None

        now = time.monotonic()
        dwell = max(0.0, now - incident.started_at)
        if now < incident.started_at:
            logger.warning("dwell_time_clock_skew", incident_id=incident_id)
            dwell = 0.0

        incident.detected = True
        incident.detected_at = now
        SECURITY_DWELL_TIME_SECONDS.labels(incident_type=incident.incident_type).observe(dwell)
        return dwell

    def _compute_blast_radius(self, agent_id: str) -> float:
        tool_calls = self._tool_calls.get(agent_id, 0)
        escalations = self._escalations.get(agent_id, 0)
        tokens = self._last.tokens if self._last and self._last.agent_id == agent_id else 0
        requests = max(self._count, 1)

        raw = (tool_calls * 2.0) + (tokens / 500.0) + (escalations * 10.0)
        normalized = raw / requests
        return min(float(self._max_score), normalized)
