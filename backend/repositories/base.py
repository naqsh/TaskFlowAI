"""Generic async repository pattern."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import Base, WorkspaceScopedMixin

T = TypeVar("T", bound=Base)


class AsyncRepository[T: Base]:
    """Base async repository with common CRUD helpers."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Fetch a single entity by primary key."""
        return await self._session.get(self._model, entity_id)

    async def add(self, entity: T) -> T:
        """Persist a new entity and flush to assign defaults."""
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Remove an entity from the session."""
        await self._session.delete(entity)
        await self._session.flush()


class WorkspaceScopedRepository[T: Base](AsyncRepository[T]):
    """Repository for models with ``workspace_id`` tenant scoping."""

    async def get_by_id_for_workspace(self, entity_id: UUID, workspace_id: UUID) -> T | None:
        """Fetch an entity scoped to a workspace."""
        if not issubclass(self._model, WorkspaceScopedMixin):
            msg = f"{self._model.__name__} is not workspace-scoped"
            raise TypeError(msg)
        stmt = select(self._model).where(
            self._model.id == entity_id,
            self._model.workspace_id == workspace_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[T]:
        """List entities for a workspace with pagination."""
        if not issubclass(self._model, WorkspaceScopedMixin):
            msg = f"{self._model.__name__} is not workspace-scoped"
            raise TypeError(msg)
        stmt = (
            select(self._model)
            .where(self._model.workspace_id == workspace_id)
            .order_by(self._model.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
