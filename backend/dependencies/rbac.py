"""Role-based access control FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User, WorkspaceMember, WorkspaceRole
from backend.dependencies.auth import bearer_scheme, decode_access_token, get_current_user
from backend.dependencies.database import get_db
from backend.exceptions import ForbiddenError, UnauthorizedError
from backend.repositories.workspace_member_repository import WorkspaceMemberRepository
from backend.security.abac import Action, PermissionContext, Resource, check_permission
from backend.settings import Settings, get_settings


@dataclass(frozen=True)
class WorkspaceAuthContext:
    """Authenticated user scoped to a workspace with a live membership role."""

    user: User
    workspace_id: UUID
    role: WorkspaceRole
    membership: WorkspaceMember


def _required_workspace_id(claims: Mapping[str, object]) -> UUID:
    workspace_id = claims.get("workspace_id")
    if not isinstance(workspace_id, str) or not workspace_id:
        raise UnauthorizedError("Missing workspace context in token")
    return UUID(workspace_id)


async def get_workspace_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkspaceAuthContext:
    """Resolve user + workspace membership from JWT (fresh DB lookup each request)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing authentication credentials")

    claims = decode_access_token(credentials.credentials, settings)
    workspace_id = _required_workspace_id(claims)

    membership_repo = WorkspaceMemberRepository(session)
    membership = await membership_repo.get_membership(user.id, workspace_id)
    if membership is None:
        raise ForbiddenError("You are not a member of this workspace")

    return WorkspaceAuthContext(
        user=user,
        workspace_id=workspace_id,
        role=WorkspaceRole(membership.role),
        membership=membership,
    )


def require_role(*roles: WorkspaceRole) -> Callable[..., object]:
    """Dependency factory requiring one of the given workspace roles."""

    allowed = set(roles)

    async def _require_role(
        ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    ) -> WorkspaceAuthContext:
        if ctx.role not in allowed:
            raise ForbiddenError("Insufficient role for this operation")
        return ctx

    return _require_role


def require_permission(
    resource: Resource,
    action: Action,
    *,
    context: PermissionContext | None = None,
) -> Callable[..., object]:
    """Dependency factory enforcing ABAC permission for the current member."""

    async def _require_permission(
        ctx: Annotated[WorkspaceAuthContext, Depends(get_workspace_auth_context)],
    ) -> WorkspaceAuthContext:
        if not check_permission(
            ctx.role,
            resource,
            action,
            actor_id=ctx.user.id,
            context=context,
        ):
            raise ForbiddenError("Permission denied for this operation")
        return ctx

    return _require_permission
