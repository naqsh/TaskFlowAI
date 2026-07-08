"""User preference routes (TF-017)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User
from backend.dependencies.auth import get_current_user
from backend.dependencies.database import get_db
from backend.repositories.user_preference_repository import UserPreferenceRepository
from backend.schemas.preferences import (
    EmailNotificationsPreferencesResponse,
    EmailNotificationsPreferencesUpdateRequest,
)

router = APIRouter(prefix="/preferences", tags=["preferences"])


def get_user_preference_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferenceRepository:
    return UserPreferenceRepository(session)


@router.get(
    "/email-notifications",
    response_model=EmailNotificationsPreferencesResponse,
)
async def get_email_notifications_pref(
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserPreferenceRepository, Depends(get_user_preference_repo)],
) -> EmailNotificationsPreferencesResponse:
    pref = await repo.get_by_user_id(user_id=current_user.id)
    enabled = bool(pref.email_notifications_enabled) if pref else True
    return EmailNotificationsPreferencesResponse(email_notifications_enabled=enabled)


@router.patch(
    "/email-notifications",
    response_model=EmailNotificationsPreferencesResponse,
)
async def update_email_notifications_pref(
    payload: EmailNotificationsPreferencesUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[UserPreferenceRepository, Depends(get_user_preference_repo)],
) -> EmailNotificationsPreferencesResponse:
    pref = await repo.set_email_notifications_enabled(
        user_id=current_user.id,
        enabled=payload.email_notifications_enabled,
    )
    return EmailNotificationsPreferencesResponse(
        email_notifications_enabled=pref.email_notifications_enabled,
    )
