"""Projects and tasks CRUD API tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from backend.db.models import WorkspaceRole
from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.dependencies.database import get_db
from backend.repositories.workspace_member_repository import WorkspaceMemberRepository
from backend.schemas.task import TaskCreate
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def crud_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping projects/tasks integration tests")
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
async def db_client(crud_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    from backend.main import create_app

    init_engine(crud_settings)
    app = create_app(crud_settings)

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


async def _register_admin(db_client: AsyncClient) -> tuple[str, UUID]:
    email = f"admin-{uuid4().hex[:8]}@example.com"
    response = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123", "full_name": "Admin User"},
    )
    assert response.status_code == 201
    access = response.json()["access_token"]
    me = await db_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    workspace_id = UUID(me.json()["workspace_id"])
    return access, workspace_id


def _auth(access: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access}"}


@pytest.mark.asyncio
async def test_empty_task_title_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": str(uuid4()),
            "title": "",
            "priority": "medium",
        },
        headers=_auth("invalid"),
    )
    assert response.status_code in {401, 422}


def test_invalid_priority_enum_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(
            {
                "project_id": uuid4(),
                "title": "Valid title",
                "priority": "not-a-priority",
            }
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_and_task_crud_cycle(db_client: AsyncClient) -> None:
    access, _workspace_id = await _register_admin(db_client)
    headers = _auth(access)

    project = await db_client.post(
        "/api/v1/projects",
        json={
            "name": "MVP Sprint",
            "description": "<b>Goals</b><script>alert(1)</script>",
        },
        headers=headers,
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    assert "<script>" not in (project.json().get("description") or "")

    listed = await db_client.get("/api/v1/projects", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == project_id for item in listed.json()["items"])

    past_due = date.today() - timedelta(days=1)
    task = await db_client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Ship TF-008",
            "description": "CRUD API<script>evil()</script>",
            "priority": "high",
            "due_date": past_due.isoformat(),
        },
        headers=headers,
    )
    assert task.status_code == 201
    task_body = task.json()
    task_id = task_body["id"]
    assert task_body["status"] == "todo"
    assert task_body["priority"] == "high"
    assert "due_date_is_in_past" in task_body["warnings"]
    assert "<script>" not in (task_body.get("description") or "")

    filtered = await db_client.get(
        f"/api/v1/tasks?project_id={project_id}&status=todo&priority=high",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert any(item["id"] == task_id for item in filtered.json()["items"])

    updated = await db_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    archived = await db_client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    deleted_project = await db_client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert deleted_project.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_in_missing_project_returns_404(db_client: AsyncClient) -> None:
    access, _ = await _register_admin(db_client)
    response = await db_client.post(
        "/api/v1/tasks",
        json={
            "project_id": str(uuid4()),
            "title": "Orphan task",
            "priority": "medium",
        },
        headers=_auth(access),
    )
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_assignee_not_in_workspace_returns_422(db_client: AsyncClient) -> None:
    access, _ = await _register_admin(db_client)
    headers = _auth(access)

    project = await db_client.post(
        "/api/v1/projects",
        json={"name": "Assignment test"},
        headers=headers,
    )
    project_id = project.json()["id"]

    response = await db_client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Bad assignee",
            "priority": "medium",
            "assignee_id": str(uuid4()),
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_member_cannot_delete_project(db_client: AsyncClient) -> None:
    access, workspace_id = await _register_admin(db_client)
    headers = _auth(access)

    project = await db_client.post(
        "/api/v1/projects",
        json={"name": "Protected project"},
        headers=headers,
    )
    project_id = project.json()["id"]

    me = await db_client.get("/api/v1/auth/me", headers=headers)
    user_id = UUID(me.json()["id"])

    init_engine(
        Settings(
            app_env="development",
            database_url=TEST_DATABASE_URL or "",
            jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
        )
    )
    async with session_scope() as session:
        repo = WorkspaceMemberRepository(session)
        membership = await repo.get_membership(user_id, workspace_id)
        assert membership is not None
        membership.role = WorkspaceRole.MEMBER
        await session.flush()

    response = await db_client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cross_workspace_task_access_returns_404(db_client: AsyncClient) -> None:
    access_a, _ = await _register_admin(db_client)
    headers_a = _auth(access_a)

    project = await db_client.post(
        "/api/v1/projects",
        json={"name": "Workspace A project"},
        headers=headers_a,
    )
    project_id = project.json()["id"]

    task = await db_client.post(
        "/api/v1/tasks",
        json={"project_id": project_id, "title": "Secret task", "priority": "low"},
        headers=headers_a,
    )
    task_id = task.json()["id"]

    access_b, _ = await _register_admin(db_client)
    response = await db_client.get(f"/api/v1/tasks/{task_id}", headers=_auth(access_b))
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
