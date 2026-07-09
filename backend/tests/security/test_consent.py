"""Tests for agentic consent flows (TF-051)."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.services.consent_service import CONSENT_SCOPE_AI, ConsentService
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


@pytest.fixture
def consent_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping consent integration tests")
    return Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
    )


@pytest.fixture(autouse=True)
async def _reset_engine() -> AsyncGenerator[None, None]:
    reset_engine()
    yield
    await dispose_engine()
    reset_engine()


async def _seed_user_workspace(session: AsyncSession) -> tuple[UUID, UUID]:
    user_id = uuid4()
    workspace_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash, full_name, is_active)
            VALUES (:id, :email, :hash, :name, true)
            """
        ),
        {
            "id": user_id,
            "email": f"consent-{user_id.hex[:8]}@example.com",
            "hash": "hashed",
            "name": "Consent User",
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO workspaces (id, name, slug)
            VALUES (:id, :name, :slug)
            """
        ),
        {"id": workspace_id, "name": "Consent WS", "slug": f"ws-{user_id.hex[:8]}"},
    )
    await session.execute(
        text(
            """
            INSERT INTO workspace_members (id, workspace_id, user_id, role)
            VALUES (:id, :ws, :uid, 'member')
            """
        ),
        {"id": uuid4(), "ws": workspace_id, "uid": user_id},
    )
    return user_id, workspace_id


@pytest.mark.asyncio
async def test_grant_and_check_consent(consent_settings: Settings) -> None:
    init_engine(consent_settings)
    async with session_scope() as session:
        user_id, workspace_id = await _seed_user_workspace(session)
        service = ConsentService(session)
        record = await service.grant(user_id=user_id, workspace_id=workspace_id)
        await session.commit()
        assert record.scope == CONSENT_SCOPE_AI
        assert await service.is_valid(user_id=user_id, workspace_id=workspace_id)


@pytest.mark.asyncio
async def test_revoked_consent_blocks_immediately(consent_settings: Settings) -> None:
    init_engine(consent_settings)
    async with session_scope() as session:
        user_id, workspace_id = await _seed_user_workspace(session)
        service = ConsentService(session)
        await service.grant(user_id=user_id, workspace_id=workspace_id)
        await service.revoke(user_id=user_id, workspace_id=workspace_id)
        await session.commit()
        assert not await service.is_valid(user_id=user_id, workspace_id=workspace_id)


@pytest.mark.asyncio
async def test_expired_consent_requires_regrant(consent_settings: Settings) -> None:
    init_engine(consent_settings)
    async with session_scope() as session:
        user_id, workspace_id = await _seed_user_workspace(session)
        now = datetime.now(UTC)
        await session.execute(
            text(
                """
                INSERT INTO consent_records
                (id, user_id, workspace_id, scope, granted_at, expires_at)
                VALUES (:id, :uid, :ws, :scope, :granted, :expires)
                """
            ),
            {
                "id": uuid4(),
                "uid": user_id,
                "ws": workspace_id,
                "scope": CONSENT_SCOPE_AI,
                "granted": now - timedelta(days=31),
                "expires": now - timedelta(days=1),
            },
        )
        await session.commit()
        service = ConsentService(session)
        assert await service.check_consent(user_id=user_id, workspace_id=workspace_id) is None
