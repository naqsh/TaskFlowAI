"""Comment business logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Comment, Task, TaskStatus
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from backend.repositories.comment_repository import CommentRepository
from backend.repositories.task_repository import TaskRepository
from backend.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from backend.security.abac import Action, PermissionContext, Resource, check_permission
from backend.security.sanitization import sanitize_comment_body
from backend.services.audit_service import AuditService

EDIT_WINDOW_MINUTES = 15


class CommentService:
    """Workspace-scoped comment CRUD with ABAC and edit window enforcement."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._comments = CommentRepository(session)
        self._tasks = TaskRepository(session)
        self._audit = AuditService()

    def _comment_permission_context(self, comment: Comment) -> PermissionContext:
        return PermissionContext(owner_id=comment.author_id)

    def _ensure_comment_permission(
        self,
        ctx: WorkspaceAuthContext,
        action: Action,
        *,
        comment: Comment | None = None,
    ) -> None:
        permission_context = (
            self._comment_permission_context(comment) if comment is not None else None
        )
        if not check_permission(
            ctx.role,
            Resource.COMMENT,
            action,
            actor_id=ctx.user.id,
            context=permission_context,
        ):
            raise ForbiddenError("Permission denied for this operation")

    async def _get_task_or_404(self, ctx: WorkspaceAuthContext, task_id: UUID) -> Task:
        task = await self._tasks.get_by_id_for_workspace(task_id, ctx.workspace_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    def _ensure_task_allows_comments(self, task: Task) -> None:
        if task.status == TaskStatus.ARCHIVED:
            raise ConflictError("Cannot comment on an archived task")

    @staticmethod
    def _sanitize_body_or_422(body: str) -> str:
        cleaned = sanitize_comment_body(body)
        if not cleaned:
            raise ValidationError("Comment body cannot be empty after sanitization")
        return cleaned

    def _ensure_within_edit_window(self, comment: Comment) -> None:
        deadline = comment.created_at + timedelta(minutes=EDIT_WINDOW_MINUTES)
        if datetime.now(UTC) > deadline:
            raise ForbiddenError("Comment edit window has expired")

    async def list_comments(
        self,
        ctx: WorkspaceAuthContext,
        task_id: UUID,
    ) -> list[CommentResponse]:
        self._ensure_comment_permission(ctx, Action.READ)
        await self._get_task_or_404(ctx, task_id)
        comments = await self._comments.list_by_task(ctx.workspace_id, task_id)
        return [CommentResponse.model_validate(comment) for comment in comments]

    async def create_comment(
        self,
        ctx: WorkspaceAuthContext,
        task_id: UUID,
        payload: CommentCreate,
    ) -> CommentResponse:
        self._ensure_comment_permission(ctx, Action.CREATE)
        task = await self._get_task_or_404(ctx, task_id)
        self._ensure_task_allows_comments(task)

        body = self._sanitize_body_or_422(payload.body)
        comment = Comment(
            workspace_id=ctx.workspace_id,
            task_id=task_id,
            author_id=ctx.user.id,
            body=body,
        )
        persisted = await self._comments.add(comment)
        await self._audit.log_event(
            actor_id=ctx.user.id,
            action="comment.created",
            resource_type="comment",
            resource_id=persisted.id,
            metadata={
                "workspace_id": str(ctx.workspace_id),
                "task_id": str(task_id),
                "comment_id": str(persisted.id),
            },
            workspace_id=ctx.workspace_id,
        )
        return CommentResponse.model_validate(persisted)

    async def update_comment(
        self,
        ctx: WorkspaceAuthContext,
        comment_id: UUID,
        payload: CommentUpdate,
    ) -> CommentResponse:
        comment = await self._comments.get_by_id_for_workspace(comment_id, ctx.workspace_id)
        if comment is None:
            raise NotFoundError("Comment not found")

        if comment.author_id != ctx.user.id:
            raise ForbiddenError("Only the comment author may edit this comment")

        self._ensure_comment_permission(ctx, Action.UPDATE, comment=comment)
        self._ensure_within_edit_window(comment)

        task = await self._get_task_or_404(ctx, comment.task_id)
        self._ensure_task_allows_comments(task)

        comment.body = self._sanitize_body_or_422(payload.body)
        await self._session.flush()
        await self._session.refresh(comment)
        return CommentResponse.model_validate(comment)

    async def delete_comment(self, ctx: WorkspaceAuthContext, comment_id: UUID) -> None:
        comment = await self._comments.get_by_id_for_workspace(comment_id, ctx.workspace_id)
        if comment is None:
            raise NotFoundError("Comment not found")

        self._ensure_comment_permission(ctx, Action.DELETE, comment=comment)
        await self._comments.delete(comment)
