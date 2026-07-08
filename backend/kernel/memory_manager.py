from __future__ import annotations

from typing import Any


class MemoryManager:
    """Memory manager scaffolds for CoALA (Part 1).

    Full working + episodic persistence is implemented in TF-E3-029.
    In Part 1 we keep minimal stubs so graph code can depend on a stable API.
    """

    def __init__(self) -> None:
        # Working memory keyed by session_id.
        self._working: dict[str, dict[str, Any]] = {}
        self._episodic: list[dict[str, Any]] = []

    def get_working(self, session_id: str) -> dict[str, Any]:
        return self._working.setdefault(session_id, {})

    async def distill_to_episodic(self, session_id: str, content: dict[str, Any]) -> None:
        self._episodic.append({"session_id": session_id, "content": content})
