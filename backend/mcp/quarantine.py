"""MCP quarantine persistence helper (TF-042)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import QuarantinedMcpResponse
from backend.logging_config import get_logger

logger = get_logger(__name__)


class QuarantineWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def write(self, *, tool: str, reason: str, raw_hash: str) -> None:
        row = QuarantinedMcpResponse(tool=tool, reason=reason, raw_hash=raw_hash)
        self._session.add(row)

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.error("quarantine_commit_failed")
            raise
