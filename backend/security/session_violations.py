from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock


class SessionViolationLimiter:
    """Rate-limit repeated security violations per session (>3/hour)."""

    def __init__(self, max_violations: int = 3, window_seconds: int = 3600) -> None:
        self._max_violations = max_violations
        self._window = timedelta(seconds=window_seconds)
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def is_blocked(self, session_key: str) -> bool:
        now = datetime.now(UTC)
        cutoff = now - self._window
        with self._lock:
            bucket = self._events[session_key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            return len(bucket) >= self._max_violations

    def record_violation(self, session_key: str) -> None:
        """Record a security violation for the session."""
        now = datetime.now(UTC)
        cutoff = now - self._window
        with self._lock:
            bucket = self._events[session_key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
