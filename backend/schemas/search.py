"""Search schemas (TF-015)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SearchItemKind(StrEnum):
    TASK = "task"
    PROJECT = "project"
    COMMENT = "comment"


class SearchResultItem(BaseModel):
    model_config = ConfigDict()

    kind: SearchItemKind
    id: UUID
    title: str | None = None
    snippet: str | None = None
    created_at: datetime | None = None
    workspace_id: UUID | None = None


class SearchResponse(BaseModel):
    model_config = ConfigDict()

    items: list[SearchResultItem]
    total: int
    q: str
