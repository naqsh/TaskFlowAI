"""Authentication endpoint and service tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from jose import jwt

from backend.db.session import dispose_engine, init_engine, reset_engine
from backend.dependencies.auth import decode_access_token
from backend.dependencies.database import get_db
from backend.exceptions import UnauthorizedError
from backend.security.rate_limit import InMemoryRateLimiter
from backend.services.auth_service import (
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        app_env="development",
        app_debug=False,
        jwt_secret_key="test-jwt-secret-key-for-unit-tests-only-32chars",
        jwt_access_token_expire_minutes=15,
        auth_login_rate_limit=3,
        auth_login_rate_window_seconds=60,
    )


def test_hash_and_verify_password_roundtrip() -> None:
    hashed = hash_password("secure-password-123")
    assert verify_password("secure-password-123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_generate_refresh_token_is_unique() -> None:
    tokens = {generate_refresh_token() for _ in range(10)}
    assert len(tokens) == 10


def test_hash_refresh_token_is_deterministic() -> None:
    token = "sample-refresh-token"
    assert hash_refresh_token(token) == hash_refresh_token(token)


def test_decode_access_token_rejects_wrong_type(auth_settings: Settings) -> None:
    payload = {
        "sub": str(uuid4()),
        "email": "user@example.com",
        "type": "refresh",
        "exp": 9999999999,
    }
    token = jwt.encode(payload, auth_settings.jwt_secret_key, algorithm="HS256")
    with pytest.raises(UnauthorizedError):
        decode_access_token(token, auth_settings)


def test_rate_limiter_blocks_after_max_requests() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.is_allowed("127.0.0.1")
    assert limiter.is_allowed("127.0.0.1")
    assert not limiter.is_allowed("127.0.0.1")


@pytest.mark.asyncio
async def test_register_password_too_short_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_me_invalid_jwt_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_me_missing_auth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.fixture
async def integration_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping auth integration tests")
    return Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
        auth_login_rate_limit=100,
    )


@pytest.fixture(autouse=True)
async def _reset_db_engine() -> AsyncGenerator[None, None]:
    reset_engine()
    yield
    await dispose_engine()
    reset_engine()


@pytest.fixture
async def db_client(integration_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    from backend.main import create_app

    init_engine(integration_settings)
    app = create_app(integration_settings)

    async def override_get_db() -> AsyncGenerator[object, None]:
        from backend.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_login_me_flow(db_client: AsyncClient) -> None:
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "secure-password-123"

    register = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Flow User"},
    )
    assert register.status_code == 201
    tokens = register.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me = await db_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    profile = me.json()
    assert profile["email"] == email
    assert profile["full_name"] == "Flow User"
    assert profile["workspace_id"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_email_returns_409(db_client: AsyncClient) -> None:
    email = f"dup-{uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "secure-password-123", "full_name": "Dup User"}

    first = await db_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await db_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["error"] == "conflict"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_detection(db_client: AsyncClient) -> None:
    email = f"refresh-{uuid4().hex[:8]}@example.com"
    register = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123", "full_name": "Refresh User"},
    )
    old_refresh = register.json()["refresh_token"]

    rotated = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reuse.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(db_client: AsyncClient) -> None:
    email = f"logout-{uuid4().hex[:8]}@example.com"
    register = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123", "full_name": "Logout User"},
    )
    refresh_token = register.json()["refresh_token"]

    logout = await db_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 204

    refresh = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(db_client: AsyncClient) -> None:
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "secure-password-123"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_rate_limit_returns_429(
    integration_settings: Settings,
) -> None:
    from backend.main import create_app

    limited_settings = integration_settings.model_copy(update={"auth_login_rate_limit": 2})
    init_engine(limited_settings)
    app = create_app(limited_settings)

    async def override_get_db() -> AsyncGenerator[object, None]:
        from backend.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as db_client:
        payload = {"email": "missing@example.com", "password": "wrong-password"}
        await db_client.post("/api/v1/auth/login", json=payload)
        await db_client.post("/api/v1/auth/login", json=payload)
        third = await db_client.post("/api/v1/auth/login", json=payload)
        assert third.status_code == 429

    app.dependency_overrides.clear()
