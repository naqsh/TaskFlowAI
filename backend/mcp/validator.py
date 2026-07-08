from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.db.models import TaskPriority


class TaskMcpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    title: str
    description: str | None = None
    priority: TaskPriority | str
    due_date: date | None = None


class ProjectMcpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None


class CommentMcpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    task_id: UUID
    body: str


class MCPResponseValidator:
    """Schema layer only — no business logic beyond minimal shape checks."""

    def validate(self, tool: str, response: Any) -> Any:
        try:
            if tool == "tasks.list":
                return self._validate_list(response, model=TaskMcpItem)
            if tool == "projects.list":
                return self._validate_list(response, model=ProjectMcpItem)
            if tool == "comments.list":
                return self._validate_list(response, model=CommentMcpItem)
        except ValidationError as e:
            raise e

        # Unknown tools are treated as raw passthrough (kernel allowlist should prevent in prod).
        return response

    @staticmethod
    def _validate_list(response: Any, *, model: type[BaseModel]) -> list[dict[str, Any]]:
        if response is None:
            return []
        if not isinstance(response, list):
            raise ValueError("expected list response from MCP")

        # Validate each item and return plain dicts to keep downstream graph state JSON-friendly.
        validated = [model.model_validate(item) for item in response]
        return [v.model_dump() for v in validated]
