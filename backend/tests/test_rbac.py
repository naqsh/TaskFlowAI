"""ABAC permission matrix tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.db.models import WorkspaceRole
from backend.security.abac import Action, PermissionContext, Resource, check_permission

ACTOR_ID = uuid4()
OTHER_ID = uuid4()


@pytest.mark.parametrize(
    ("role", "resource", "action", "expected"),
    [
        (WorkspaceRole.ADMIN, Resource.PROJECT, Action.DELETE, True),
        (WorkspaceRole.ADMIN, Resource.WORKSPACE, Action.MANAGE, True),
        (WorkspaceRole.MANAGER, Resource.PROJECT, Action.DELETE, True),
        (WorkspaceRole.MANAGER, Resource.PROJECT, Action.CREATE, True),
        (WorkspaceRole.MANAGER, Resource.TASK, Action.ASSIGN, True),
        (WorkspaceRole.MANAGER, Resource.WORKSPACE, Action.MANAGE, False),
        (WorkspaceRole.MANAGER, Resource.MEMBER, Action.DELETE, False),
        (WorkspaceRole.MEMBER, Resource.PROJECT, Action.DELETE, False),
        (WorkspaceRole.MEMBER, Resource.PROJECT, Action.READ, True),
        (WorkspaceRole.MEMBER, Resource.TASK, Action.READ, True),
        (WorkspaceRole.MEMBER, Resource.TASK, Action.DELETE, False),
        (WorkspaceRole.MEMBER, Resource.TASK, Action.CREATE, False),
        (WorkspaceRole.MEMBER, Resource.WORKSPACE, Action.MANAGE, False),
    ],
)
def test_permission_matrix(
    role: WorkspaceRole,
    resource: Resource,
    action: Action,
    expected: bool,
) -> None:
    assert check_permission(role, resource, action, actor_id=ACTOR_ID) is expected, (
        f"{role} {resource} {action}"
    )


def test_member_can_update_own_task() -> None:
    context = PermissionContext(owner_id=ACTOR_ID)
    assert check_permission(
        WorkspaceRole.MEMBER,
        Resource.TASK,
        Action.UPDATE,
        actor_id=ACTOR_ID,
        context=context,
    )


def test_member_can_update_assigned_task() -> None:
    context = PermissionContext(assignee_id=ACTOR_ID)
    assert check_permission(
        WorkspaceRole.MEMBER,
        Resource.TASK,
        Action.UPDATE,
        actor_id=ACTOR_ID,
        context=context,
    )


def test_member_cannot_update_others_task() -> None:
    context = PermissionContext(owner_id=OTHER_ID, assignee_id=OTHER_ID)
    assert not check_permission(
        WorkspaceRole.MEMBER,
        Resource.TASK,
        Action.UPDATE,
        actor_id=ACTOR_ID,
        context=context,
    )


def test_member_can_edit_own_comment() -> None:
    context = PermissionContext(owner_id=ACTOR_ID)
    assert check_permission(
        WorkspaceRole.MEMBER,
        Resource.COMMENT,
        Action.UPDATE,
        actor_id=ACTOR_ID,
        context=context,
    )


def test_member_cannot_edit_others_comment() -> None:
    context = PermissionContext(owner_id=OTHER_ID)
    assert not check_permission(
        WorkspaceRole.MEMBER,
        Resource.COMMENT,
        Action.DELETE,
        actor_id=ACTOR_ID,
        context=context,
    )


def test_manager_can_delete_project() -> None:
    assert check_permission(
        WorkspaceRole.MANAGER,
        Resource.PROJECT,
        Action.DELETE,
        actor_id=ACTOR_ID,
    )


def test_all_roles_accept_string_values() -> None:
    assert check_permission("admin", Resource.TASK, Action.READ, actor_id=ACTOR_ID)
    assert check_permission("member", Resource.PROJECT, Action.READ, actor_id=ACTOR_ID)
