"""User preference persistence (TF-017)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UserPreference


class UserPreferenceRepository:
    """Repository for per-user preference flags."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, *, user_id: UUID) -> UserPreference | None:
        stmt = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_email_notifications_enabled(
        self, *, user_id: UUID, enabled: bool
    ) -> UserPreference:
        pref = await self.get_by_user_id(user_id=user_id)
        if pref is None:
            pref = UserPreference(user_id=user_id, email_notifications_enabled=enabled)
            self._session.add(pref)
        else:
            pref.email_notifications_enabled = enabled
        await self._session.flush()
        await self._session.refresh(pref)
        return pref
