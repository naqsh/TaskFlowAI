from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient
from jose import jwt

from backend.rate_limit_middleware import CompositeRateLimiter


@pytest.mark.asyncio
async def test_rate_limit_429_after_threshold_uses_redis(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ensure JWT decoding uses our secret in middleware's get_settings().
    secret = "test-jwt-secret-key-for-rate-limit-tests-only-32chars"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    fake_redis = FakeRedis()

    async def _fake_try_get_redis(self: CompositeRateLimiter) -> FakeRedis:
        return fake_redis

    monkeypatch.setattr(CompositeRateLimiter, "_try_get_redis", _fake_try_get_redis)

    user_id = "11111111-1111-4111-8111-111111111111"
    email = "user@example.com"
    exp = int((datetime.now(UTC) + timedelta(minutes=10)).timestamp())
    token = jwt.encode(
        {"sub": user_id, "email": email, "type": "access", "exp": exp},
        secret,
        algorithm="HS256",
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Forwarded-For": "9.9.9.9",
    }

    last = None
    for _ in range(100):
        last = await client.get("/api/v1/ping", headers=headers)
        assert last.status_code == 200

    last = await client.get("/api/v1/ping", headers=headers)
    assert last.status_code == 429
    assert "Retry-After" in last.headers


@pytest.mark.asyncio
async def test_rate_limit_resets_after_window(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-jwt-secret-key-for-rate-limit-tests-only-32chars"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    fake_redis = FakeRedis()

    async def _fake_try_get_redis(self: CompositeRateLimiter) -> FakeRedis:
        return fake_redis

    monkeypatch.setattr(CompositeRateLimiter, "_try_get_redis", _fake_try_get_redis)

    user_id = "22222222-2222-4222-8222-222222222222"
    email = "user2@example.com"
    exp = int((datetime.now(UTC) + timedelta(minutes=10)).timestamp())
    token = jwt.encode(
        {"sub": user_id, "email": email, "type": "access", "exp": exp},
        secret,
        algorithm="HS256",
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Forwarded-For": "10.10.10.10",
    }

    # Force time to a fixed bucket; then advance beyond the window.
    import backend.rate_limit_middleware as m

    current_time = 100000.0

    def _fake_time() -> float:
        return current_time

    monkeypatch.setattr(m.time, "time", _fake_time)  # type: ignore[attr-defined]

    for _ in range(100):
        resp = await client.get("/api/v1/ping", headers=headers)
        assert resp.status_code == 200

    resp = await client.get("/api/v1/ping", headers=headers)
    assert resp.status_code == 429

    current_time += 61.0

    resp = await client.get("/api/v1/ping", headers=headers)
    assert resp.status_code == 200
