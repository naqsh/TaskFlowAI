"""ORM model metadata tests."""

from backend.db import models as _models  # noqa: F401
from backend.db.base import Base
from backend.db.models import (
    AuditLog,
    Comment,
    Project,
    Task,
    User,
    Workspace,
    WorkspaceMember,
)


def test_models_register_on_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users",
        "workspaces",
        "workspace_members",
        "projects",
        "tasks",
        "comments",
        "audit_logs",
    }
    assert expected.issubset(table_names)


def test_tenant_tables_include_workspace_id() -> None:
    for model in (Project, Task, Comment):
        assert "workspace_id" in model.__table__.columns


def test_all_primary_keys_are_uuid() -> None:
    for model in (User, Workspace, WorkspaceMember, Project, Task, Comment, AuditLog):
        id_column = model.__table__.columns["id"]
        assert "UUID" in str(id_column.type)


def test_models_import_without_circular_dependency() -> None:
    """Smoke test — importing models package should not raise."""
    assert User.__tablename__ == "users"
    assert Task.__tablename__ == "tasks"
