"""TF-011 tests: audit log + OpenTelemetry trace_id baseline."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.db.models import AuditLog
from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.dependencies.database import get_db
from backend.main import create_app
from backend.settings import Settings


@pytest.mark.asyncio
async def test_trace_id_header_is_echoed(client: AsyncClient) -> None:
    # Must be a 32-hex `trace_id`.
    trace_id = uuid4().hex
    response = await client.get("/health", headers={"X-Trace-Id": trace_id})
    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == trace_id.lower()


@pytest.mark.asyncio
async def test_trace_span_correlation_matches_x_trace_id() -> None:
    """Stronger TF-011 assertion than echoing the header.

    We install an in-memory exporter and assert the `http.request` span has the
    expected `trace_id`.
    """

    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    settings = Settings(
        app_env="development",
        app_debug=False,
        jwt_secret_key="test-jwt-secret-key-for-unit-tests-only-32chars",
        otel_exporter_otlp_endpoint="",  # disable OTLP export during this test
    )
    app = create_app(settings)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Prime ASGI lifespan so `create_app()`-startup doesn't overwrite our tracer provider.
        await ac.get("/health")

        exporter = InMemorySpanExporter()
        provider = TracerProvider(resource=Resource.create({"service.name": "taskflow-ai"}))
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        otel_trace.set_tracer_provider(provider)

        trace_id = uuid4().hex.lower()
        await ac.get("/health", headers={"X-Trace-Id": trace_id})

        finished = exporter.get_finished_spans()
        matching = [
            span
            for span in finished
            if span.name == "http.request" and f"{span.context.trace_id:032x}" == trace_id
        ]
        assert matching, "Expected an `http.request` span with the same trace_id as X-Trace-Id"


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def integration_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping audit log integration test")
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_create_writes_audit_log_with_correct_actor_id(db_client: AsyncClient) -> None:
    # Register + authenticate admin.
    email = f"aud-{uuid4().hex[:8]}@example.com"
    password = "secure-password-123"
    register = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Audit User"},
    )
    assert register.status_code == 201
    tokens = register.json()

    me = await db_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    user_id = UUID(me.json()["id"])
    workspace_id = UUID(me.json()["workspace_id"])

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Create a project.
    project_resp = await db_client.post(
        "/api/v1/projects",
        json={"name": f"proj-{uuid4().hex[:6]}", "description": "Audit test"},
        headers=headers,
    )
    assert project_resp.status_code == 201
    project_id = UUID(project_resp.json()["id"])

    # Create a task.
    task_resp = await db_client.post(
        "/api/v1/tasks",
        json={"project_id": str(project_id), "title": "TF-011 task", "priority": "medium"},
        headers=headers,
    )
    assert task_resp.status_code == 201
    task_id = UUID(task_resp.json()["id"])

    # Verify audit log entry exists and is attributed to the actor.
    async with session_scope() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == "task.created")
            .where(AuditLog.actor_id == user_id)
            .where(AuditLog.resource_type == "task")
            .where(AuditLog.resource_id == task_id)
            .where(AuditLog.workspace_id == workspace_id)
        )
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
