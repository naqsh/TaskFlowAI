"""Agentic AI consent records and enforcement (TF-051)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ConsentRecord
from backend.exceptions import ForbiddenError

CONSENT_SCOPE_AI = "ai_assistance"
CONSENT_TTL_DAYS = 30
ALLOWED_SCOPES = frozenset({CONSENT_SCOPE_AI})


class ConsentService:
    """Time-bounded workspace-scoped AI consent management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def grant(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        scope: str = CONSENT_SCOPE_AI,
        ttl_days: int = CONSENT_TTL_DAYS,
    ) -> ConsentRecord:
        if scope not in ALLOWED_SCOPES:
            raise ForbiddenError("Invalid consent scope")

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=ttl_days)

        # Supersede prior records for same user/workspace/scope.
        stmt = select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.workspace_id == workspace_id,
            ConsentRecord.scope == scope,
            ConsentRecord.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        for existing in result.scalars().all():
            existing.revoked_at = now

        record = ConsentRecord(
            user_id=user_id,
            workspace_id=workspace_id,
            scope=scope,
            granted_at=now,
            expires_at=expires_at,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def revoke(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        scope: str = CONSENT_SCOPE_AI,
    ) -> None:
        now = datetime.now(UTC)
        stmt = select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.workspace_id == workspace_id,
            ConsentRecord.scope == scope,
            ConsentRecord.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        for record in result.scalars().all():
            record.revoked_at = now
        await self._session.flush()

    async def check_consent(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        scope: str = CONSENT_SCOPE_AI,
    ) -> ConsentRecord | None:
        now = datetime.now(UTC)
        stmt = (
            select(ConsentRecord)
            .where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.workspace_id == workspace_id,
                ConsentRecord.scope == scope,
                ConsentRecord.revoked_at.is_(None),
                ConsentRecord.expires_at > now,
            )
            .order_by(ConsentRecord.granted_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_valid(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        scope: str = CONSENT_SCOPE_AI,
    ) -> bool:
        return (
            await self.check_consent(
                user_id=user_id,
                workspace_id=workspace_id,
                scope=scope,
            )
            is not None
        )

    async def has_consent(self, user_id: UUID, workspace_id: UUID) -> bool:
        """Protocol-compatible helper for CredentialBroker."""
        return await self.is_valid(user_id=user_id, workspace_id=workspace_id)
