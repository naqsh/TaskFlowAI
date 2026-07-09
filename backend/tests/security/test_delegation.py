"""Tests for DelegationContext framework (TF-049)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from backend.kernel.identity_manager import IdentityManager
from backend.security.delegation import (
    ConfusedDeputyError,
    DelegationExpiredError,
    DelegationPermissionError,
    create_delegation,
    validate_delegation,
)


def test_valid_context_passes_validation() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="sess-1",
        agent_id="context_agent",
        intent="read_tasks",
        parent_trace_id="abc123",
    )
    validate_delegation(ctx, tool="tasks.list")
    assert ctx.parent_trace_id == "abc123"


def test_expired_context_raises() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="sess-1",
        agent_id="context_agent",
        intent="read_tasks",
        ttl_seconds=60,
    )
    expired_now = ctx.expires_at + timedelta(seconds=60)
    with pytest.raises(DelegationExpiredError):
        validate_delegation(ctx, now=expired_now)


def test_intent_mismatch_raises_confused_deputy() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="sess-1",
        agent_id="context_agent",
        intent="read_projects",
    )
    with pytest.raises(ConfusedDeputyError):
        validate_delegation(ctx, tool="tasks.list")


def test_ttl_clamped_to_900() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="sess-1",
        agent_id="context_agent",
        intent="read_tasks",
        ttl_seconds=1800,
    )
    delta = ctx.expires_at - ctx.issued_at
    assert delta.total_seconds() <= 900


def test_missing_permission_denied() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="sess-1",
        agent_id="context_agent",
        intent="read_tasks",
    )
    with pytest.raises(DelegationPermissionError):
        validate_delegation(ctx, required_permission="tasks:update")


def test_grace_window_allows_near_expiry() -> None:
    ctx = create_delegation(
        user_id=uuid4(),
        session_id="sess-1",
        agent_id="context_agent",
        intent="read_tasks",
        ttl_seconds=60,
        grace_seconds=30,
    )
    within_grace = ctx.expires_at + timedelta(seconds=15)
    validate_delegation(ctx, now=within_grace, grace_seconds=30)


@pytest.mark.asyncio
async def test_revoked_session_invalidates_delegation() -> None:
    manager = IdentityManager()
    user_id = uuid4()
    ctx = await manager.create_delegation_context(
        user_id=user_id,
        agent_id="context_agent",
        intent="read_tasks",
        session_id="revoked-session",
    )
    manager.revoke_session("revoked-session")
    with pytest.raises(Exception, match="revoked"):
        manager.validate_delegation_context(ctx, tool="tasks.list")
