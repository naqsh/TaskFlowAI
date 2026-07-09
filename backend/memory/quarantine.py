"""RAG poisoning quarantine stub (TF-062) — active when vector search is enabled."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class QuarantinedDocument:
    id: UUID
    source_uri: str
    reason: str
    quarantined_at: datetime


class RAGQuarantineStore:
    """In-memory quarantine stub until vector search ingestion ships."""

    def __init__(self) -> None:
        self._entries: dict[UUID, QuarantinedDocument] = {}

    def quarantine(self, *, source_uri: str, reason: str) -> QuarantinedDocument:
        entry = QuarantinedDocument(
            id=uuid4(),
            source_uri=source_uri,
            reason=reason,
            quarantined_at=datetime.now(UTC),
        )
        self._entries[entry.id] = entry
        return entry

    def list_quarantined(self) -> list[QuarantinedDocument]:
        return sorted(self._entries.values(), key=lambda e: e.quarantined_at, reverse=True)

    def is_quarantined(self, source_uri: str) -> bool:
        return any(e.source_uri == source_uri for e in self._entries.values())
