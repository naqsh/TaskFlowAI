"""Refresh token persistence for JWT rotation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RefreshToken
from backend.repositories.base import AsyncRepository


class RefreshTokenRepository(AsyncRepository[RefreshToken]):
    """Repository for server-side refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Fetch a refresh token record by its hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, *, replaced_by_id: UUID | None = None) -> None:
        """Mark a refresh token as revoked."""
        token.revoked_at = datetime.now(UTC)
        if replaced_by_id is not None:
            token.replaced_by_id = replaced_by_id
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke all active refresh tokens for a user."""
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        now = datetime.now(UTC)
        for token in result.scalars():
            token.revoked_at = now
        await self._session.flush()
