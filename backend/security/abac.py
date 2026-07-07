"""Attribute-based access control for workspace resources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from backend.db.models import WorkspaceRole


class Resource(StrEnum):
    """Protected resource types within a workspace."""

    WORKSPACE = "workspace"
    PROJECT = "project"
    TASK = "task"
    COMMENT = "comment"
    MEMBER = "member"


class Action(StrEnum):
    """Actions that can be performed on resources."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ASSIGN = "assign"
    MANAGE = "manage"


@dataclass(frozen=True)
class PermissionContext:
    """Optional attributes for ABAC decisions (e.g. task ownership)."""

    owner_id: UUID | None = None
    assignee_id: UUID | None = None


def _member_can_modify_task(actor_id: UUID, context: PermissionContext | None) -> bool:
    if context is None:
        return False
    if context.owner_id == actor_id:
        return True
    return context.assignee_id == actor_id


def check_permission(
    role: WorkspaceRole | str,
    resource: Resource,
    action: Action,
    *,
    actor_id: UUID,
    context: PermissionContext | None = None,
) -> bool:
    """Return whether the role may perform action on resource within a workspace."""
    resolved_role = WorkspaceRole(role)

    if resolved_role == WorkspaceRole.ADMIN:
        return True

    if resolved_role == WorkspaceRole.MANAGER:
        if resource == Resource.WORKSPACE and action == Action.MANAGE:
            return False
        if resource == Resource.MEMBER and action in {Action.DELETE, Action.MANAGE}:
            return False
        if resource == Resource.PROJECT:
            return action in {Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE}
        if resource == Resource.TASK:
            return action in {
                Action.CREATE,
                Action.READ,
                Action.UPDATE,
                Action.DELETE,
                Action.ASSIGN,
            }
        if resource == Resource.COMMENT:
            return action in {Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE}
        if resource == Resource.MEMBER:
            return action == Action.READ
        return False

    # MEMBER — least privilege
    if resource == Resource.WORKSPACE:
        return action == Action.READ
    if resource == Resource.PROJECT:
        return action == Action.READ
    if resource == Resource.TASK:
        if action == Action.READ:
            return True
        if action in {Action.CREATE, Action.UPDATE}:
            return _member_can_modify_task(actor_id, context)
        return False
    if resource == Resource.COMMENT:
        if action in {Action.CREATE, Action.READ}:
            return True
        if action in {Action.UPDATE, Action.DELETE}:
            return context is not None and context.owner_id == actor_id
        return False
    if resource == Resource.MEMBER:
        return action == Action.READ and context is not None and context.owner_id == actor_id

    return False
