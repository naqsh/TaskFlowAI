"""User preference schemas (TF-017)."""

from __future__ import annotations

from pydantic import BaseModel


class EmailNotificationsPreferencesResponse(BaseModel):
    email_notifications_enabled: bool


class EmailNotificationsPreferencesUpdateRequest(BaseModel):
    email_notifications_enabled: bool
