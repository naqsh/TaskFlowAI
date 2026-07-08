from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.kernel.errors import MCPValidationError
from backend.kernel.security_monitor import SecurityMonitor
from backend.mcp.validator import MCPResponseValidator


def _task_item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "project_id": uuid4(),
        "title": "Clean task",
        "description": None,
        "priority": "medium",
        "due_date": date(2026, 1, 1),
    }
    base.update(overrides)
    return base


def test_script_tag_stripped_from_title() -> None:
    monitor = SecurityMonitor()
    validator = MCPResponseValidator(security_monitor=monitor, default_size_threshold=1000)
    item = _task_item(title="<script>alert(1)</script>Real title")
    out = validator.validate("tasks.list", [item])
    assert "<script>" not in out[0]["title"]
    assert "Real title" in out[0]["title"]


def test_schema_violation_raises_validation_error() -> None:
    validator = MCPResponseValidator()
    with pytest.raises(ValidationError):
        validator.validate("tasks.list", [{"id": uuid4()}])


def test_oversized_response_triggers_quarantine() -> None:
    monitor = SecurityMonitor()
    validator = MCPResponseValidator(
        security_monitor=monitor,
        default_size_threshold=100,
    )
    huge_title = "x" * 2000
    item = _task_item(title=huge_title)
    with pytest.raises(MCPValidationError, match="quarantined"):
        validator.validate("tasks.list", [item])


def test_anomaly_detection_on_10x_baseline() -> None:
    monitor = SecurityMonitor()
    validator = MCPResponseValidator(
        security_monitor=monitor,
        default_size_threshold=500,
        anomaly_sigma=2.0,
    )
    normal = _task_item(title="normal")
    for _ in range(5):
        validator.validate("tasks.list", [normal], latency_ms=1.0)

    huge = _task_item(title="x" * 5000)
    with pytest.raises(MCPValidationError):
        validator.validate("tasks.list", [huge], latency_ms=1.0)


def test_internal_url_blocked() -> None:
    monitor = SecurityMonitor()
    validator = MCPResponseValidator(security_monitor=monitor)
    item = _task_item(description="See http://192.168.1.1/internal")
    with pytest.raises(MCPValidationError, match="internal_url"):
        validator.validate("tasks.list", [item])
