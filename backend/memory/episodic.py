from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class EpisodicEntryData:
    user_id: UUID
    session_id: str
    lesson_type: str
    content: dict[str, Any]
    version: int


class EpisodicMemory:
    """Episodic memory store (Part 1 foundation).

    Part 2 will replace this with a PostgreSQL-backed implementation via
    SQLAlchemy. In Part 1 we support an in-memory mode so unit tests can
    validate isolation semantics.
    """

    def __init__(self) -> None:
        self._entries: list[EpisodicEntryData] = []

    async def write_entry(
        self,
        *,
        user_id: UUID,
        session_id: str,
        lesson_type: str,
        content: dict[str, Any],
        version: int = 1,
    ) -> None:
        self._entries.append(
            EpisodicEntryData(
                user_id=user_id,
                session_id=session_id,
                lesson_type=lesson_type,
                content=content,
                version=version,
            )
        )

    async def read_entries(
        self,
        *,
        user_id: UUID,
        session_id: str,
        lesson_type: str | None = None,
    ) -> list[EpisodicEntryData]:
        entries = [
            e
            for e in self._entries
            if e.user_id == user_id
            and e.session_id == session_id
            and (lesson_type is None or e.lesson_type == lesson_type)
        ]
        # Return stable order: newest version last.
        return sorted(entries, key=lambda e: e.version)

    async def read_latest(
        self,
        *,
        user_id: UUID,
        session_id: str,
        lesson_type: str,
    ) -> dict[str, Any] | None:
        entries = await self.read_entries(
            user_id=user_id, session_id=session_id, lesson_type=lesson_type
        )
        if not entries:
            return None
        return entries[-1].content
