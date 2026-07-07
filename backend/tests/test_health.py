"""Health and metrics endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_includes_trace_id_header(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "X-Trace-Id" in response.headers
    assert len(response.headers["X-Trace-Id"]) > 0


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(client: AsyncClient) -> None:
    await client.get("/health")
    response = await client.get("/metrics/", follow_redirects=True)
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "api_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_api_v1_ping(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
