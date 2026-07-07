"""IDOR prevention and workspace isolation tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from backend.db.models import Project, Task, TaskPriority, TaskStatus, WorkspaceRole
from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.dependencies.database import get_db
from backend.dependencies.rbac import _required_workspace_id
from backend.exceptions import UnauthorizedError
from backend.repositories.task_repository import TaskRepository
from backend.repositories.workspace_member_repository import WorkspaceMemberRepository
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def test_missing_workspace_id_in_claims_raises_401() -> None:
    with pytest.raises(UnauthorizedError, match="Missing workspace context"):
        _required_workspace_id({"sub": str(uuid4()), "email": "a@b.com"})


@pytest.mark.asyncio
async def test_cross_workspace_task_lookup_returns_none() -> None:
    """Cross-workspace access returns None (API layer maps to 404, not 403)."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")

    settings = Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
    )
    reset_engine()
    init_engine(settings)

    workspace_a = uuid4()
    workspace_b = uuid4()
    user_id = uuid4()
    project_id = uuid4()

    try:
        async with session_scope() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, full_name, is_active) "
                    "VALUES (:id, :email, :hash, :name, true)"
                ),
                {
                    "id": user_id,
                    "email": f"idor-{user_id.hex[:8]}@example.com",
                    "hash": "hashed",
                    "name": "IDOR User",
                },
            )
            for ws_id, slug in [(workspace_a, "ws-a"), (workspace_b, "ws-b")]:
                await session.execute(
                    text("INSERT INTO workspaces (id, name, slug) VALUES (:id, :name, :slug)"),
                    {"id": ws_id, "name": slug, "slug": f"{slug}-{ws_id.hex[:6]}"},
                )
            session.add(
                Project(
                    id=project_id,
                    workspace_id=workspace_a,
                    name="Project A",
                    created_by=user_id,
                )
            )
            await session.flush()

            repo = TaskRepository(session)
            task = await repo.add(
                Task(
                    workspace_id=workspace_a,
                    project_id=project_id,
                    title="Scoped task",
                    status=TaskStatus.TODO,
                    priority=TaskPriority.MEDIUM,
                    created_by=user_id,
                )
            )

            assert await repo.get_by_id_for_workspace(task.id, workspace_a) is not None
            assert await repo.get_by_id_for_workspace(task.id, workspace_b) is None
    finally:
        await dispose_engine()
        reset_engine()


@pytest.fixture
async def db_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
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


@pytest.fixture
async def db_client(db_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    from backend.main import create_app

    init_engine(db_settings)
    app = create_app(db_settings)

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
async def test_removed_member_gets_403_on_protected_context(db_client: AsyncClient) -> None:
    """User removed from workspace mid-session receives 403 on next RBAC check."""
    email = f"removed-{uuid4().hex[:8]}@example.com"
    register = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123", "full_name": "Removed User"},
    )
    assert register.status_code == 201
    tokens = register.json()
    access = tokens["access_token"]
    me = await db_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    workspace_id = UUID(me.json()["workspace_id"])

    init_engine(
        Settings(
            app_env="development",
            database_url=TEST_DATABASE_URL or "",
            jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
        )
    )
    user_id = UUID(me.json()["id"])
    async with session_scope() as session:
        repo = WorkspaceMemberRepository(session)
        membership = await repo.get_membership(user_id, workspace_id)
        assert membership is not None
        await session.execute(
            text("DELETE FROM workspace_members WHERE id = :id"),
            {"id": membership.id},
        )

    response = await db_client.get(
        "/api/v1/workspaces/current",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_demoted_admin_gets_member_permissions_immediately(db_client: AsyncClient) -> None:
    """Role demotion takes effect on the next request (fresh DB lookup)."""
    email = f"demoted-{uuid4().hex[:8]}@example.com"
    register = await db_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-password-123", "full_name": "Demoted Admin"},
    )
    tokens = register.json()
    access = tokens["access_token"]
    me = await db_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    workspace_id = UUID(me.json()["workspace_id"])
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

    response = await db_client.get(
        "/api/v1/workspaces/current",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == WorkspaceRole.MEMBER
