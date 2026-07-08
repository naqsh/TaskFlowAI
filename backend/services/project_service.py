"""Project business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Project
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.exceptions import ForbiddenError, NotFoundError
from backend.repositories.project_repository import ProjectRepository
from backend.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from backend.security.abac import Action, Resource, check_permission
from backend.security.sanitization import sanitize_description


class ProjectService:
    """Workspace-scoped project CRUD."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectRepository(session)

    def _ensure_permission(
        self,
        ctx: WorkspaceAuthContext,
        action: Action,
    ) -> None:
        if not check_permission(ctx.role, Resource.PROJECT, action, actor_id=ctx.user.id):
            raise ForbiddenError("Permission denied for this operation")

    async def list_projects(
        self,
        ctx: WorkspaceAuthContext,
        *,
        limit: int,
        offset: int,
    ) -> list[ProjectResponse]:
        self._ensure_permission(ctx, Action.READ)
        projects = await self._projects.list_ordered(
            ctx.workspace_id,
            limit=limit,
            offset=offset,
        )
        return [ProjectResponse.model_validate(project) for project in projects]

    async def get_project(self, ctx: WorkspaceAuthContext, project_id: UUID) -> ProjectResponse:
        self._ensure_permission(ctx, Action.READ)
        project = await self._projects.get_by_id_for_workspace(project_id, ctx.workspace_id)
        if project is None:
            raise NotFoundError("Project not found")
        return ProjectResponse.model_validate(project)

    async def create_project(
        self,
        ctx: WorkspaceAuthContext,
        payload: ProjectCreate,
    ) -> ProjectResponse:
        self._ensure_permission(ctx, Action.CREATE)
        project = Project(
            workspace_id=ctx.workspace_id,
            name=payload.name,
            description=sanitize_description(payload.description),
            created_by=ctx.user.id,
        )
        persisted = await self._projects.add(project)
        return ProjectResponse.model_validate(persisted)

    async def update_project(
        self,
        ctx: WorkspaceAuthContext,
        project_id: UUID,
        payload: ProjectUpdate,
    ) -> ProjectResponse:
        self._ensure_permission(ctx, Action.UPDATE)
        project = await self._projects.get_by_id_for_workspace(project_id, ctx.workspace_id)
        if project is None:
            raise NotFoundError("Project not found")

        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = sanitize_description(payload.description)

        await self._session.flush()
        await self._session.refresh(project)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, ctx: WorkspaceAuthContext, project_id: UUID) -> None:
        self._ensure_permission(ctx, Action.DELETE)
        project = await self._projects.get_by_id_for_workspace(project_id, ctx.workspace_id)
        if project is None:
            raise NotFoundError("Project not found")
        await self._projects.delete(project)
