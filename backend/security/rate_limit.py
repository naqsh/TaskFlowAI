"""Simple in-memory rate limiter for auth endpoints."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock


class InMemoryRateLimiter:
    """Fixed-window rate limiter keyed by client identifier."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window = timedelta(seconds=window_seconds)
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Return True if the key is within the configured rate limit."""
        now = datetime.now(UTC)
        cutoff = now - self._window
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True


def get_client_ip(
    *,
    forwarded_for: str | None,
    client_host: str | None,
) -> str:
    """Resolve client IP from proxy headers or direct connection."""
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return client_host or "unknown"
