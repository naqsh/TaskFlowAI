"""Task repository unit tests."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Task, TaskPriority, TaskStatus
from backend.repositories.task_repository import TaskRepository


@pytest.mark.asyncio
async def test_task_repository_list_by_workspace_executes_scoped_query() -> None:
    workspace_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalar_result
    session.execute.return_value = execute_result

    repo = TaskRepository(session)
    tasks = await repo.list_by_workspace(workspace_id)

    assert tasks == []
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_task_repository_add_persists_task() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TaskRepository(session)
    task = Task(
        workspace_id=uuid4(),
        project_id=uuid4(),
        title="Integration test task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        created_by=uuid4(),
    )
    persisted = await repo.add(task)

    session.add.assert_called_once_with(task)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(task)
    assert persisted is task
