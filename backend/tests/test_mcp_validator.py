from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.mcp.validator import MCPResponseValidator


def test_mcp_validator_tasks_list_valid() -> None:
    v = MCPResponseValidator()
    item = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "project_id": uuid4(),
        "title": "Test task",
        "description": None,
        "priority": "medium",
        "due_date": date(2026, 1, 1),
    }
    out = v.validate("tasks.list", [item])
    assert isinstance(out, list)
    assert out[0]["title"] == "Test task"


def test_mcp_validator_tasks_list_rejects_missing_fields() -> None:
    v = MCPResponseValidator()
    with pytest.raises(ValidationError):
        v.validate("tasks.list", [{"id": uuid4()}])


def test_mcp_validator_none_response_becomes_empty_list() -> None:
    v = MCPResponseValidator()
    out = v.validate("projects.list", None)
    assert out == []
