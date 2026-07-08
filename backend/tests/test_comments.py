"""Comment API and sanitization tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import text

from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.dependencies.database import get_db
from backend.schemas.comment import CommentCreate
from backend.security.sanitization import sanitize_comment_body
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def comment_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping comment integration tests")
    return Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
    )


@pytest.fixture(autouse=True)
async def _reset_db_engine() -> AsyncGenerator[None, None]:
    reset_engine()
    yield
    await dispose_engine()
    reset_engine()


@pytest.fixture
async def db_client(comment_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    from backend.main import create_app

    init_engine(comment_settings)
    app = create_app(comment_settings)

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


async def _register_admin(db_client: AsyncClient) -> str:
    email = f"admin-{uuid4().hex[:8]}@example.com"
    response = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123", "full_name": "Admin User"},
    )
    assert response.status_code == 201
    token: str = response.json()["access_token"]
    return token


def _auth(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


async def _create_project_and_task(db_client: AsyncClient, access: str) -> tuple[str, str]:
    headers = _auth(access)
    project = await db_client.post(
        "/api/v1/projects",
        json={"name": "Comments project"},
        headers=headers,
    )
    project_id = project.json()["id"]
    task = await db_client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Commentable task", "priority": "medium"},
        headers=headers,
    )
    return project_id, task.json()["id"]


def test_sanitize_comment_body_strips_script_tags() -> None:
    cleaned = sanitize_comment_body("<p>Hi</p><script>alert(1)</script>")
    assert "<script>" not in cleaned
    assert "alert" not in cleaned
    assert "<p>Hi</p>" in cleaned


def test_sanitize_comment_body_allows_safe_tags() -> None:
    cleaned = sanitize_comment_body("<strong>Bold</strong> and <em>italic</em>")
    assert "<strong>Bold</strong>" in cleaned
    assert "<em>italic</em>" in cleaned


def test_empty_comment_body_schema_validation() -> None:
    with pytest.raises(ValidationError):
        CommentCreate.model_validate({"body": ""})


def test_comment_body_max_length_validation() -> None:
    with pytest.raises(ValidationError):
        CommentCreate.model_validate({"body": "x" * 10001})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_crud_cycle(db_client: AsyncClient) -> None:
    access = await _register_admin(db_client)
    headers = _auth(access)
    _project_id, task_id = await _create_project_and_task(db_client, access)

    created = await db_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"body": "<p>Looks good</p><script>alert(1)</script>"},
        headers=headers,
    )
    assert created.status_code == 201
    comment = created.json()
    comment_id = comment["id"]
    assert "<script>" not in comment["body"]
    assert "Looks good" in comment["body"]

    listed = await db_client.get(f"/api/v1/tasks/{task_id}/comments", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == comment_id for item in listed.json()["items"])

    updated = await db_client.patch(
        f"/api/v1/comments/{comment_id}",
        json={"body": "<em>Updated</em>"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert "<em>Updated</em>" in updated.json()["body"]

    deleted = await db_client.delete(f"/api/v1/comments/{comment_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_author_cannot_edit_comment(db_client: AsyncClient) -> None:
    access_a = await _register_admin(db_client)
    _project_id, task_id = await _create_project_and_task(db_client, access_a)

    created = await db_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"body": "Author comment"},
        headers=_auth(access_a),
    )
    comment_id = created.json()["id"]

    access_b = await _register_admin(db_client)
    response = await db_client.patch(
        f"/api/v1/comments/{comment_id}",
        json={"body": "Hijacked"},
        headers=_auth(access_b),
    )
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_on_archived_task_returns_409(db_client: AsyncClient) -> None:
    access = await _register_admin(db_client)
    headers = _auth(access)
    _project_id, task_id = await _create_project_and_task(db_client, access)

    archived = await db_client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert archived.status_code == 200

    response = await db_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"body": "Too late"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_on_missing_task_returns_404(db_client: AsyncClient) -> None:
    access = await _register_admin(db_client)
    response = await db_client.post(
        f"/api/v1/tasks/{uuid4()}/comments",
        json={"body": "Orphan comment"},
        headers=_auth(access),
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_comment_edit_window_expires(db_client: AsyncClient) -> None:
    access = await _register_admin(db_client)
    headers = _auth(access)
    _project_id, task_id = await _create_project_and_task(db_client, access)

    created = await db_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"body": "Old comment"},
        headers=headers,
    )
    comment_id = UUID(created.json()["id"])

    init_engine(
        Settings(
            app_env="development",
            database_url=TEST_DATABASE_URL or "",
            jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
        )
    )
    stale_time = datetime.now(UTC) - timedelta(minutes=20)
    async with session_scope() as session:
        await session.execute(
            text("UPDATE comments SET created_at = :ts, updated_at = :ts WHERE id = :id"),
            {"ts": stale_time, "id": comment_id},
        )

    response = await db_client.patch(
        f"/api/v1/comments/{comment_id}",
        json={"body": "Late edit"},
        headers=headers,
    )
    assert response.status_code == 403
