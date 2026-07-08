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
TEST_JWT_SECRET = "test-jwt-secret-key-for-integration-tests-attachments-32c"


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
async def test_attachment_upload_validates_and_downloads(
    db_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_JWT_SECRET)

    init_engine(db_settings)
    app = create_app(db_settings)
    transport = ASGITransport(app=app)

    workspace_id = uuid4()
    admin_user_id = uuid4()
    project_id = uuid4()

    async with session_scope() as session:
        session.add(
            User(
                id=admin_user_id,
                email="admin-attach@example.com",
                password_hash="hashed",
                full_name="Admin Attach",
                is_active=True,
            )
        )
        await session.flush()

        session.add(Workspace(id=workspace_id, name="WS", slug=f"ws-{workspace_id.hex[:8]}"))
        await session.flush()

        session.add(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=admin_user_id,
                role=WorkspaceRole.ADMIN,
            )
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

    token = _make_token(
        user_id=str(admin_user_id),
        email="admin-attach@example.com",
        workspace_id=str(workspace_id),
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created_task = await client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": str(project_id),
                "title": "Task for attachment",
                "description": None,
                "priority": TaskPriority.MEDIUM.value,
                "due_date": None,
                "assignee_id": None,
            },
        )
        assert created_task.status_code == 201
        task_id = created_task.json()["id"]

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"a" * 1024
        upload = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert upload.status_code == 201
        body = upload.json()
        assert body["mime_type"] == "image/png"
        attachment_id = body["id"]

        download_url = body["download_url"]
        token_param = download_url.split("token=", 1)[1]

        download_ok = await client.get(
            f"/api/v1/attachments/{attachment_id}/download?token={token_param}"
        )
        assert download_ok.status_code == 200
        assert len(download_ok.content) == len(png_bytes)

        download_bad = await client.get(f"/api/v1/attachments/{attachment_id}/download?token=bad")
        assert download_bad.status_code == 403

        # Reject unsupported mime
        exe_bytes = b"MZ" + b"a" * 100
        upload_exe = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("bad.exe", exe_bytes, "application/x-msdownload")},
        )
        assert upload_exe.status_code == 415

        # Reject >10MB
        big_bytes = b"a" * (10 * 1024 * 1024 + 1)
        upload_big = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("big.txt", big_bytes, "text/plain")},
        )
        assert upload_big.status_code == 413
