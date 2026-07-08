"""Database integration tests — require TEST_DATABASE_URL."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import text

from backend.db.models import Project, Task, TaskPriority, TaskStatus
from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.repositories.task_repository import TaskRepository
from backend.settings import Settings

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
async def db_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping database integration tests")
    return Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-jwt-secret-key-for-integration-tests-32c",
    )


@pytest.fixture(autouse=True)
async def _reset_engine() -> AsyncIterator[None]:
    reset_engine()
    yield
    await dispose_engine()
    reset_engine()


@pytest.mark.asyncio
async def test_insert_task_and_query_by_workspace_id(db_settings: Settings) -> None:
    init_engine(db_settings)
    workspace_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()

    async with session_scope() as session:
        await session.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, full_name, is_active)
                VALUES (:id, :email, :hash, :name, true)
                """
            ),
            {
                "id": user_id,
                "email": f"user-{user_id.hex[:8]}@example.com",
                "hash": "hashed-password",
                "name": "Integration User",
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO workspaces (id, name, slug)
                VALUES (:id, :name, :slug)
                """
            ),
            {
                "id": workspace_id,
                "name": "Test Workspace",
                "slug": f"ws-{workspace_id.hex[:8]}",
            },
        )
        project = Project(
            id=project_id,
            workspace_id=workspace_id,
            name="Test Project",
            created_by=user_id,
        )
        session.add(project)
        await session.flush()

        repo = TaskRepository(session)
        task = await repo.add(
            Task(
                workspace_id=workspace_id,
                project_id=project_id,
                title="Workspace scoped task",
                status=TaskStatus.TODO,
                priority=TaskPriority.HIGH,
                created_by=user_id,
            )
        )

        fetched = await repo.get_by_id_for_workspace(task.id, workspace_id)
        assert fetched is not None
        assert fetched.title == "Workspace scoped task"

        other_workspace = uuid4()
        assert await repo.get_by_id_for_workspace(task.id, other_workspace) is None

        listed = await repo.list_by_workspace(workspace_id)
        assert len(listed) == 1
        assert listed[0].id == task.id
