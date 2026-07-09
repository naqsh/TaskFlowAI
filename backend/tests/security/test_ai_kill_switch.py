"""Tests for AI_FEATURES_ENABLED kill switch (TF-061)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from backend.settings import Settings


@pytest.mark.asyncio
async def test_ai_kill_switch_returns_503() -> None:
    settings = Settings(ai_features_enabled=False)
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ai/parse-task",
            json={"nl_input": "test"},
        )
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "service_unavailable"


@pytest.mark.asyncio
async def test_health_unaffected_by_kill_switch() -> None:
    settings = Settings(ai_features_enabled=False)
    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
