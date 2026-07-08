"""DLQ event schemas (TF-043)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DLQReason = Literal[
    "security_violation_detected",
    "verification_failed",
    "mcp_timeout",
    "mcp_validation_failed",
    "max_retries_exceeded",
    "failure",
]

DLQStatus = Literal["pending", "permanently_failed", "retried"]


class DLQEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: UUID
    user_id: UUID | None = None
    workspace_id: UUID | None = None
    agent_id: str | None = None
    reason: DLQReason
    envelope_json: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0


class DLQEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: UUID
    request_id: UUID
    user_id: UUID | None
    workspace_id: UUID | None
    agent_id: str | None
    reason: str
    status: str
    envelope_json: dict[str, Any]
    retry_count: int
    created_at: datetime


class DLQListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    items: list[DLQEventResponse]
    total: int
    limit: int
    offset: int
