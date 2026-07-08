"""Search business logic (TF-015)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import TaskPriority, TaskStatus
from backend.dependencies.rbac import WorkspaceAuthContext
from backend.repositories.search_repository import SearchRepository
from backend.schemas.search import SearchItemKind, SearchResultItem
from backend.security.abac import Action, Resource, check_permission


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SearchRepository(session)

    async def search(
        self,
        *,
        ctx: WorkspaceAuthContext,
        q: str | None,
        type_filter: str | None,
        project_id: UUID | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: UUID | None,
        due_before: date | None,
        due_after: date | None,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[SearchResultItem], int]:
        if not check_permission(
            ctx.role,
            Resource.TASK,
            Action.READ,
            actor_id=ctx.user.id,
        ) and not check_permission(
            ctx.role,
            Resource.PROJECT,
            Action.READ,
            actor_id=ctx.user.id,
        ):
            # Conservatively deny when role doesn't allow any resource search.
            return ([], 0)

        requested = (type_filter or "tasks").lower()
        include_tasks = requested in {"tasks", "all"}
        include_projects = requested in {"projects", "all"}
        include_comments = requested in {"comments", "all"}

        items: list[SearchResultItem] = []

        if include_tasks:
            tasks = await self._repo.search_tasks(
                workspace_id=ctx.workspace_id,
                q=q,
                project_id=project_id,
                status=status,
                priority=priority,
                assignee_id=assignee_id,
                due_before=due_before,
                due_after=due_after,
                include_archived=include_archived,
                limit=limit,
                offset=offset,
            )
            for t in tasks:
                items.append(
                    SearchResultItem(
                        kind=SearchItemKind.TASK,
                        id=t.id,
                        title=t.title,
                        snippet=t.description,
                        created_at=t.created_at,
                        workspace_id=t.workspace_id,
                    )
                )

        if include_projects:
            projects = await self._repo.search_projects(
                workspace_id=ctx.workspace_id,
                q=q,
                project_id=project_id,
                include_archived=include_archived,
                limit=limit,
                offset=offset,
            )
            for p in projects:
                items.append(
                    SearchResultItem(
                        kind=SearchItemKind.PROJECT,
                        id=p.id,
                        title=p.name,
                        snippet=p.description,
                        created_at=p.created_at,
                        workspace_id=p.workspace_id,
                    )
                )

        if include_comments:
            comments = await self._repo.search_comments(
                workspace_id=ctx.workspace_id,
                q=q,
                project_id=project_id,
                status=status,
                priority=priority,
                assignee_id=assignee_id,
                due_before=due_before,
                due_after=due_after,
                include_archived=include_archived,
                limit=limit,
                offset=offset,
            )
            for c in comments:
                items.append(
                    SearchResultItem(
                        kind=SearchItemKind.COMMENT,
                        id=c.id,
                        title=None,
                        snippet=c.body,
                        created_at=c.created_at,
                        workspace_id=c.workspace_id,
                    )
                )

        # YOLO: total is best-effort since we don't compute full counts per-kind.
        return (items[:limit], len(items))
