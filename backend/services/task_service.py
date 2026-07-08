"""Task business logic."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Task, TaskPriority, TaskStatus
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.exceptions import ForbiddenError, NotFoundError, ValidationError
from backend.repositories.project_repository import ProjectRepository
from backend.repositories.task_repository import TaskRepository
from backend.repositories.workspace_member_repository import WorkspaceMemberRepository
from backend.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from backend.security.abac import Action, PermissionContext, Resource, check_permission
from backend.security.sanitization import sanitize_description
from backend.services.audit_service import AuditService


class TaskService:
    """Workspace-scoped task CRUD with ABAC enforcement."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskRepository(session)
        self._projects = ProjectRepository(session)
        self._members = WorkspaceMemberRepository(session)
        self._audit = AuditService()

    def _task_permission_context(self, task: Task) -> PermissionContext:
        return PermissionContext(
            owner_id=task.created_by,
            assignee_id=task.assignee_id,
        )

    def _ensure_task_permission(
        self,
        ctx: WorkspaceAuthContext,
        action: Action,
        *,
        task: Task | None = None,
        owner_id: UUID | None = None,
    ) -> None:
        permission_context: PermissionContext | None
        if task is not None:
            permission_context = self._task_permission_context(task)
        elif owner_id is not None:
            permission_context = PermissionContext(owner_id=owner_id)
        else:
            permission_context = None

        if not check_permission(
            ctx.role,
            Resource.TASK,
            action,
            actor_id=ctx.user.id,
            context=permission_context,
        ):
            raise ForbiddenError("Permission denied for this operation")

    async def _validate_assignee(self, ctx: WorkspaceAuthContext, assignee_id: UUID | None) -> None:
        if assignee_id is None:
            return
        membership = await self._members.get_membership(assignee_id, ctx.workspace_id)
        if membership is None:
            raise ValidationError(
                "Assignee is not a member of this workspace",
                details={"field": "assignee_id"},
            )

    async def _get_task_or_404(self, ctx: WorkspaceAuthContext, task_id: UUID) -> Task:
        task = await self._tasks.get_by_id_for_workspace(task_id, ctx.workspace_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    @staticmethod
    def _due_date_warnings(due_date: date | None) -> list[str]:
        if due_date is not None and due_date < datetime.now(UTC).date():
            return ["due_date_is_in_past"]
        return []

    def _to_response(self, task: Task, *, warnings: list[str] | None = None) -> TaskResponse:
        response = TaskResponse.model_validate(task)
        if warnings:
            response.warnings = warnings
        return response

    async def list_tasks(
        self,
        ctx: WorkspaceAuthContext,
        *,
        project_id: UUID | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        limit: int,
        offset: int,
    ) -> list[TaskResponse]:
        self._ensure_task_permission(ctx, Action.READ)
        if project_id is not None:
            project = await self._projects.get_by_id_for_workspace(project_id, ctx.workspace_id)
            if project is None:
                raise NotFoundError("Project not found")

        tasks = await self._tasks.list_filtered(
            ctx.workspace_id,
            project_id=project_id,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset,
        )
        return [self._to_response(task) for task in tasks]

    async def get_task(self, ctx: WorkspaceAuthContext, task_id: UUID) -> TaskResponse:
        self._ensure_task_permission(ctx, Action.READ)
        task = await self._get_task_or_404(ctx, task_id)
        return self._to_response(task)

    async def create_task(self, ctx: WorkspaceAuthContext, payload: TaskCreate) -> TaskResponse:
        self._ensure_task_permission(ctx, Action.CREATE, owner_id=ctx.user.id)

        project = await self._projects.get_by_id_for_workspace(
            payload.project_id,
            ctx.workspace_id,
        )
        if project is None:
            raise NotFoundError("Project not found")

        await self._validate_assignee(ctx, payload.assignee_id)

        warnings = self._due_date_warnings(payload.due_date)
        task = Task(
            workspace_id=ctx.workspace_id,
            project_id=payload.project_id,
            title=payload.title,
            description=sanitize_description(payload.description),
            priority=payload.priority,
            due_date=payload.due_date,
            assignee_id=payload.assignee_id,
            created_by=ctx.user.id,
        )
        persisted = await self._tasks.add(task)
        # Write audit log in a separate transaction so failures never break the main request.
        await self._audit.log_event(
            actor_id=ctx.user.id,
            action="task.created",
            resource_type="task",
            resource_id=persisted.id,
            metadata={
                "workspace_id": str(ctx.workspace_id),
                "project_id": str(persisted.project_id),
                "task_id": str(persisted.id),
            },
            workspace_id=ctx.workspace_id,
        )
        return self._to_response(persisted, warnings=warnings)

    async def update_task(
        self,
        ctx: WorkspaceAuthContext,
        task_id: UUID,
        payload: TaskUpdate,
    ) -> TaskResponse:
        task = await self._get_task_or_404(ctx, task_id)
        self._ensure_task_permission(ctx, Action.UPDATE, task=task)

        if payload.assignee_id is not None:
            await self._validate_assignee(ctx, payload.assignee_id)

        if payload.title is not None:
            task.title = payload.title
        if payload.description is not None:
            task.description = sanitize_description(payload.description)
        if payload.status is not None:
            task.status = payload.status
        if payload.priority is not None:
            task.priority = payload.priority
        if "due_date" in payload.model_fields_set:
            task.due_date = payload.due_date

        assignee_set = "assignee_id" in payload.model_fields_set
        if assignee_set:
            if not check_permission(
                ctx.role,
                Resource.TASK,
                Action.ASSIGN,
                actor_id=ctx.user.id,
            ):
                raise ForbiddenError("Permission denied for task assignment")
            task.assignee_id = payload.assignee_id

        await self._session.flush()
        await self._session.refresh(task)
        warnings = self._due_date_warnings(task.due_date)
        await self._audit.log_event(
            actor_id=ctx.user.id,
            action="task.updated",
            resource_type="task",
            resource_id=task.id,
            metadata={
                "workspace_id": str(ctx.workspace_id),
                "project_id": str(task.project_id),
                "task_id": str(task.id),
                "new_status": task.status,
            },
            workspace_id=ctx.workspace_id,
        )
        return self._to_response(task, warnings=warnings)

    async def archive_task(self, ctx: WorkspaceAuthContext, task_id: UUID) -> TaskResponse:
        task = await self._get_task_or_404(ctx, task_id)
        self._ensure_task_permission(ctx, Action.DELETE, task=task)
        previous_status = task.status
        task.status = TaskStatus.ARCHIVED
        await self._session.flush()
        await self._session.refresh(task)
        await self._audit.log_event(
            actor_id=ctx.user.id,
            action="task.deleted",
            resource_type="task",
            resource_id=task.id,
            metadata={
                "workspace_id": str(ctx.workspace_id),
                "project_id": str(task.project_id),
                "task_id": str(task.id),
                "previous_status": previous_status,
            },
            workspace_id=ctx.workspace_id,
        )
        return self._to_response(task)
