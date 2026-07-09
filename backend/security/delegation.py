"""Delegation context framework for confused-deputy prevention (TF-049)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

DelegationIntent = Literal[
    "read_tasks",
    "read_projects",
    "read_comments",
    "create_task",
    "update_task",
    "none",
]

MAX_DELEGATION_TTL_SECONDS = 900
DEFAULT_GRACE_SECONDS = 30

INTENT_PERMISSIONS: dict[DelegationIntent, list[str]] = {
    "read_tasks": ["tasks:read"],
    "read_projects": ["projects:read"],
    "read_comments": ["comments:read"],
    "create_task": ["tasks:create"],
    "update_task": ["tasks:update"],
    "none": [],
}

TOOL_INTENT_MAP: dict[str, DelegationIntent] = {
    "tasks.list": "read_tasks",
    "projects.list": "read_projects",
    "comments.list": "read_comments",
}


class DelegationError(Exception):
    """Base delegation validation error."""


class DelegationExpiredError(DelegationError):
    """Raised when a delegation context has expired."""


class ConfusedDeputyError(DelegationError):
    """Raised when agent intent does not match requested MCP tool."""


class DelegationPermissionError(DelegationError):
    """Raised when delegation lacks required permission."""


class DelegationRevokedError(DelegationError):
    """Raised when the parent session has been revoked."""


@dataclass(frozen=True)
class DelegationContext:
    """User-scoped delegation token propagated API → graph → MCP."""

    user_id: UUID
    session_id: str
    agent_id: str
    intent: DelegationIntent
    permissions: list[str]
    issued_at: datetime
    expires_at: datetime
    parent_trace_id: str | None = None
    revoked: bool = False


def create_delegation(
    *,
    user_id: UUID,
    session_id: str,
    agent_id: str,
    intent: DelegationIntent,
    parent_trace_id: str | None = None,
    ttl_seconds: int = MAX_DELEGATION_TTL_SECONDS,
    grace_seconds: int = DEFAULT_GRACE_SECONDS,
) -> DelegationContext:
    """Issue a new delegation context with TTL clamped to 900s."""
    if ttl_seconds <= 0:
        msg = "ttl_seconds must be > 0"
        raise ValueError(msg)
    clamped_ttl = min(ttl_seconds, MAX_DELEGATION_TTL_SECONDS)
    now = datetime.now(UTC)
    return DelegationContext(
        user_id=user_id,
        session_id=session_id,
        agent_id=agent_id,
        intent=intent,
        permissions=list(INTENT_PERMISSIONS.get(intent, [])),
        issued_at=now,
        expires_at=now + timedelta(seconds=clamped_ttl),
        parent_trace_id=parent_trace_id,
    )


def validate_delegation(
    ctx: DelegationContext,
    *,
    tool: str | None = None,
    required_permission: str | None = None,
    grace_seconds: int = DEFAULT_GRACE_SECONDS,
    now: datetime | None = None,
) -> None:
    """Validate delegation is active and matches tool intent (confused deputy check)."""
    if ctx.revoked:
        raise DelegationRevokedError("delegation_revoked")

    current = now or datetime.now(UTC)
    effective_expiry = ctx.expires_at + timedelta(seconds=grace_seconds)
    if current > effective_expiry:
        raise DelegationExpiredError("delegation_expired")

    if required_permission and required_permission not in ctx.permissions:
        raise DelegationPermissionError(f"missing_permission permission={required_permission}")

    if tool is not None:
        expected_intent = TOOL_INTENT_MAP.get(tool)
        if expected_intent is not None and ctx.intent != expected_intent:
            raise ConfusedDeputyError(
                f"intent_mismatch tool={tool} intent={ctx.intent} expected={expected_intent}"
            )
