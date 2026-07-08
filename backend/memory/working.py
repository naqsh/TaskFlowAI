from __future__ import annotations

import json
from typing import Any


class WorkingMemory:
    """Working memory store (Part 1 foundation).

    If a Redis client is provided, we use it with a TTL; otherwise we fall back
    to an in-memory dict (unit-test friendly).
    """

    def __init__(self, *, redis_client: Any | None = None, ttl_seconds: int = 3600) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        self._in_memory: dict[str, str] = {}

    def _key(self, session_id: str) -> str:
        return f"taskflow:wm:{session_id}"

    async def set_state(self, session_id: str, state: dict[str, Any]) -> None:
        payload = json.dumps(state, default=str)
        key = self._key(session_id)
        if self._redis is None:
            self._in_memory[key] = payload
            return

        # Redis client contract: `setex(key, ttl_seconds, value)`.
        await self._redis.setex(key, self._ttl_seconds, payload)

    async def get_state(self, session_id: str) -> dict[str, Any]:
        key = self._key(session_id)
        if self._redis is None:
            raw = self._in_memory.get(key)
        else:
            raw = await self._redis.get(key)

        if raw is None:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
