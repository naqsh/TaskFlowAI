from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.db.models import AuditLog, Task, TaskStatus, User, WorkspaceMember, WorkspaceRole
from backend.db.session import dispose_engine, init_engine, reset_engine, session_scope
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.repositories.notification_repository import NotificationRepository
from backend.services.due_reminder_service import DueReminderService
from backend.settings import Settings

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def db_settings() -> Settings:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")
    return Settings(
        app_env="development",
        database_url=TEST_DATABASE_URL,
        jwt_secret_key="test-jwt-secret-key-for-integration-tests-32chars",
    )


@pytest.fixture(autouse=True)
async def _reset_engine() -> AsyncGenerator[None, None]:
    reset_engine()
    yield
    await dispose_engine()
    reset_engine()


@pytest.mark.asyncio
async def test_due_reminder_creates_notification_and_email(db_settings: Settings) -> None:
    init_engine(db_settings)

    workspace_id = uuid4()
    admin_user_id = uuid4()
    assignee_user_id = uuid4()
    project_id = uuid4()

    due_date = date.today() + timedelta(days=1)

    async with session_scope() as session:
        session.add_all(
            [
                User(
                    id=admin_user_id,
                    email="admin@example.com",
                    password_hash="hashed",
                    full_name="Admin",
                    is_active=True,
                ),
                User(
                    id=assignee_user_id,
                    email="assignee@example.com",
                    password_hash="hashed",
                    full_name="Assignee",
                    is_active=True,
                ),
            ]
        )
        await session.flush()

        # Workspace
        from backend.db.models import Workspace

        workspace = Workspace(id=workspace_id, name="WS", slug=f"ws-{workspace_id.hex[:8]}")
        session.add(workspace)
        await session.flush()

        # Membership
        session.add_all(
            [
                WorkspaceMember(
                    workspace_id=workspace_id,
                    user_id=admin_user_id,
                    role=WorkspaceRole.ADMIN,
                ),
                WorkspaceMember(
                    workspace_id=workspace_id,
                    user_id=assignee_user_id,
                    role=WorkspaceRole.MEMBER,
                ),
            ]
        )
        await session.flush()

        # Project
        from backend.db.models import Project

        project = Project(
            id=project_id,
            workspace_id=workspace_id,
            name="P",
            description=None,
            created_by=admin_user_id,
        )
        session.add(project)
        await session.flush()

        # Task due tomorrow and assigned to assignee
        task = Task(
            workspace_id=workspace_id,
            project_id=project_id,
            title="Fix login timeout",
            description=None,
            status=TaskStatus.TODO,
            priority="medium",
            due_date=due_date,
            assignee_id=assignee_user_id,
            created_by=admin_user_id,
        )
        session.add(task)
        await session.flush()

        # Auth context: run as admin member.
        admin = await session.get(User, admin_user_id)
        assert admin is not None
        membership = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == admin_user_id,
                )
            )
        ).scalar_one_or_none()
        assert membership is not None
        ctx = WorkspaceAuthContext(
            user=admin,
            workspace_id=workspace_id,
            role=WorkspaceRole(membership.role),
            membership=membership,
        )

        service = DueReminderService(session)
        processed = await service.run_for_workspace(ctx=ctx, due_date=due_date)
        assert processed == 1

    async with session_scope() as session:
        repo = NotificationRepository(session)
        unread = await repo.list_unread_for_user(
            workspace_id=workspace_id, user_id=assignee_user_id, limit=50, offset=0
        )
        assert len(unread) == 1
        assert unread[0].type == "task.due_reminder"

        audit_stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "email.sent",
                AuditLog.resource_type == "task",
                AuditLog.metadata_["email_type"].astext == "task_due_reminder",
            )
            .order_by(AuditLog.created_at.desc())
        )
        email_logs = list((await session.execute(audit_stmt)).scalars().all())
        assert len(email_logs) == 1


@pytest.mark.asyncio
async def test_due_reminder_respects_opt_out(db_settings: Settings) -> None:
    init_engine(db_settings)

    workspace_id = uuid4()
    admin_user_id = uuid4()
    assignee_user_id = uuid4()
    project_id = uuid4()

    due_date = date.today() + timedelta(days=1)

    async with session_scope() as session:
        session.add_all(
            [
                User(
                    id=admin_user_id,
                    email="admin2@example.com",
                    password_hash="hashed",
                    full_name="Admin2",
                    is_active=True,
                ),
                User(
                    id=assignee_user_id,
                    email="assignee2@example.com",
                    password_hash="hashed",
                    full_name="Assignee2",
                    is_active=True,
                ),
            ]
        )
        await session.flush()

        from backend.db.models import Project, UserPreference, Workspace

        workspace = Workspace(id=workspace_id, name="WS", slug=f"ws-{workspace_id.hex[:8]}")
        session.add(workspace)
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
                    user_id=assignee_user_id,
                    role=WorkspaceRole.MEMBER,
                ),
            ]
        )
        await session.flush()

        project = Project(
            id=project_id,
            workspace_id=workspace_id,
            name="P",
            description=None,
            created_by=admin_user_id,
        )
        session.add(project)
        await session.flush()

        task = Task(
            workspace_id=workspace_id,
            project_id=project_id,
            title="Due task - opt out",
            description=None,
            status=TaskStatus.TODO,
            priority="medium",
            due_date=due_date,
            assignee_id=assignee_user_id,
            created_by=admin_user_id,
        )
        session.add(task)
        await session.flush()

        session.add(UserPreference(user_id=assignee_user_id, email_notifications_enabled=False))
        await session.flush()

        admin = await session.get(User, admin_user_id)
        assert admin is not None
        membership = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == admin_user_id,
                )
            )
        ).scalar_one_or_none()
        assert membership is not None
        ctx = WorkspaceAuthContext(
            user=admin,
            workspace_id=workspace_id,
            role=WorkspaceRole(membership.role),
            membership=membership,
        )

        service = DueReminderService(session)
        processed = await service.run_for_workspace(ctx=ctx, due_date=due_date)
        assert processed == 1

    async with session_scope() as session:
        repo = NotificationRepository(session)
        unread = await repo.list_unread_for_user(
            workspace_id=workspace_id, user_id=assignee_user_id, limit=50, offset=0
        )
        assert len(unread) == 1

        audit_stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "email.sent",
                AuditLog.resource_type == "task",
                AuditLog.metadata_["email_type"].astext == "task_due_reminder",
            )
            .order_by(AuditLog.created_at.desc())
        )
        email_logs = list((await session.execute(audit_stmt)).scalars().all())
        assert len(email_logs) == 0


@pytest.mark.asyncio
async def test_due_reminder_skips_completed_tasks(db_settings: Settings) -> None:
    init_engine(db_settings)

    workspace_id = uuid4()
    admin_user_id = uuid4()
    assignee_user_id = uuid4()
    project_id = uuid4()

    due_date = date.today() + timedelta(days=1)

    async with session_scope() as session:
        session.add_all(
            [
                User(
                    id=admin_user_id,
                    email="admin3@example.com",
                    password_hash="hashed",
                    full_name="Admin3",
                    is_active=True,
                ),
                User(
                    id=assignee_user_id,
                    email="assignee3@example.com",
                    password_hash="hashed",
                    full_name="Assignee3",
                    is_active=True,
                ),
            ]
        )
        await session.flush()

        from backend.db.models import Project, Workspace

        workspace = Workspace(id=workspace_id, name="WS", slug=f"ws-{workspace_id.hex[:8]}")
        session.add(workspace)
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
                    user_id=assignee_user_id,
                    role=WorkspaceRole.MEMBER,
                ),
            ]
        )
        await session.flush()

        project = Project(
            id=project_id,
            workspace_id=workspace_id,
            name="P",
            description=None,
            created_by=admin_user_id,
        )
        session.add(project)
        await session.flush()

        session.add(
            Task(
                workspace_id=workspace_id,
                project_id=project_id,
                title="Completed due task",
                description=None,
                status=TaskStatus.DONE,
                priority="medium",
                due_date=due_date,
                assignee_id=assignee_user_id,
                created_by=admin_user_id,
            )
        )
        await session.flush()

        admin = await session.get(User, admin_user_id)
        assert admin is not None
        membership = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == admin_user_id,
                )
            )
        ).scalar_one_or_none()
        assert membership is not None
        ctx = WorkspaceAuthContext(
            user=admin,
            workspace_id=workspace_id,
            role=WorkspaceRole(membership.role),
            membership=membership,
        )

        service = DueReminderService(session)
        processed = await service.run_for_workspace(ctx=ctx, due_date=due_date)
        assert processed == 0

    async with session_scope() as session:
        repo = NotificationRepository(session)
        unread = await repo.list_unread_for_user(
            workspace_id=workspace_id, user_id=assignee_user_id, limit=50, offset=0
        )
        assert len(unread) == 0
