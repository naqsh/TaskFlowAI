from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from backend.db.models import (
    Project,
    TaskPriority,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.main import create_app
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_JWT_SECRET = "test-jwt-secret-key-for-integration-tests-collab-flow-32c"


def _make_token(*, user_id: str, email: str, workspace_id: str) -> str:
    exp = int((datetime.now(UTC) + timedelta(minutes=10)).timestamp())
    token_any = jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "type": "access",
            "exp": exp,
            "workspace_id": workspace_id,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    assert isinstance(token_any, str)
    return token_any


@pytest.fixture
def db_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")
    return Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key=TEST_JWT_SECRET,
    )


@pytest.fixture(autouse=True)
async def _reset_engine() -> AsyncGenerator[None, None]:
    reset_engine()
    yield
    await dispose_engine()
    reset_engine()


@pytest.mark.asyncio
async def test_assign_comment_activity_and_search_flow(
    db_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)

    init_engine(db_settings)
    app = create_app(db_settings)
    transport = ASGITransport(app=app)

    workspace_id = uuid4()
    admin_user_id = uuid4()
    member_user_id = uuid4()
    project_id = uuid4()

    due_comment_keyword = "login timeout"

    async with session_scope() as session:
        session.add_all(
            [
                User(
                    id=admin_user_id,
                    email="admin-collab@example.com",
                    password_hash="hashed",
                    full_name="Admin Collab",
                    is_active=True,
                ),
                User(
                    id=member_user_id,
                    email="member-collab@example.com",
                    password_hash="hashed",
                    full_name="Member Collab",
                    is_active=True,
                ),
            ]
        )
        await session.flush()

        session.add(
            Workspace(
                id=workspace_id,
                name="WS",
                slug=f"ws-{workspace_id.hex[:8]}",
            )
        )
        await session.flush()

        session.add_all(
            [
                WorkspaceMember(
                    workspace_id=workspace_id,
                    user_id=admin_user_id,
                    role=WorkspaceRole.ADMIN,
                ),
                WorkspaceMember(
                    workspace_id=workspace_id,
                    user_id=member_user_id,
                    role=WorkspaceRole.MEMBER,
                ),
            ]
        )
        await session.flush()

        session.add(
            Project(
                id=project_id,
                workspace_id=workspace_id,
                name="Project A",
                description=None,
                created_by=admin_user_id,
            )
        )
        await session.flush()

    admin_token = _make_token(
        user_id=str(admin_user_id),
        email="admin-collab@example.com",
        workspace_id=str(workspace_id),
    )
    member_token = _make_token(
        user_id=str(member_user_id),
        email="member-collab@example.com",
        workspace_id=str(workspace_id),
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a task (no assignee yet)
        created = await client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "project_id": str(project_id),
                "title": "Fix login timeout",
                "description": None,
                "priority": TaskPriority.MEDIUM.value,
                "due_date": None,
                "assignee_id": None,
            },
        )
        assert created.status_code == 201
        task = created.json()
        task_id = task["id"]

        # Assign task to member -> should create assignment notification
        updated = await client.patch(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"assignee_id": str(member_user_id)},
        )
        assert updated.status_code == 200

        notifications_resp = await client.get(
            "/api/v1/notifications?limit=50&offset=0",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert notifications_resp.status_code == 200
        notifications = notifications_resp.json()["items"]
        assert len(notifications) == 1
        assert notifications[0]["type"] == "task.assigned"

        # Admin adds comment -> creates comment notification for member
        comment_resp = await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"body": f"{due_comment_keyword} needs investigation"},
        )
        assert comment_resp.status_code == 201

        notifications_resp2 = await client.get(
            "/api/v1/notifications?limit=50&offset=0",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert notifications_resp2.status_code == 200
        notifications2 = notifications_resp2.json()["items"]
        assert {n["type"] for n in notifications2} == {"task.assigned", "comment.added"}

        # Activity timeline includes comment.created + task.updated
        activity_resp = await client.get(
            f"/api/v1/tasks/{task_id}/activity?limit=50&offset=0",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert activity_resp.status_code == 200
        activities = activity_resp.json()["items"]
        assert any(a["action"] == "task.updated" for a in activities)
        assert any(a["action"] == "comment.created" for a in activities)

        # Search for comment keyword
        search_resp = await client.get(
            "/api/v1/search",
            headers={"Authorization": f"Bearer {member_token}"},
            params={"q": due_comment_keyword, "type": "comments", "limit": 10, "offset": 0},
        )
        assert search_resp.status_code == 200
        search_items = search_resp.json()["items"]
        assert any(i["kind"] == "comment" for i in search_items)
