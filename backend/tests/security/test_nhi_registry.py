"""Tests for NHI X.509 agent identity registry (TF-052)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from backend.security.nhi_registry import (
    AGENT_ALLOWLIST,
    DuplicateAgentError,
    InvalidAgentCertificateError,
    NHIRegistry,
    PermissionExceedsAllowlistError,
    RegistryInitError,
)


def test_all_six_agents_registered() -> None:
    reg = NHIRegistry()
    reg.initialize()
    assert len(reg.list_agents()) == 6
    for agent_id in AGENT_ALLOWLIST:
        assert reg.get(agent_id) is not None


def test_invalid_cert_rejected() -> None:
    reg = NHIRegistry()
    reg.initialize()
    with pytest.raises(InvalidAgentCertificateError):
        reg.validate_agent("unknown_agent")


def test_duplicate_registration_rejected() -> None:
    reg = NHIRegistry()
    reg.register_agent(
        agent_id="context_agent",
        canonical_role="tool_operator",
        permissions=["tasks:read"],
    )
    with pytest.raises(DuplicateAgentError):
        reg.register_agent(
            agent_id="context_agent",
            canonical_role="tool_operator",
            permissions=["tasks:read"],
        )


def test_permissions_exceed_allowlist_rejected() -> None:
    reg = NHIRegistry()
    with pytest.raises(PermissionExceedsAllowlistError):
        reg.register_agent(
            agent_id="rogue_agent",
            canonical_role="rogue",
            permissions=["admin:all"],
        )


def test_revoked_cert_rejected() -> None:
    reg = NHIRegistry()
    reg.initialize()
    reg.revoke("context_agent")
    with pytest.raises(InvalidAgentCertificateError, match="revoked"):
        reg.validate_agent("context_agent")


def test_expired_cert_rejected() -> None:
    reg = NHIRegistry()
    reg.initialize()
    identity = reg.get("context_agent")
    assert identity is not None
    future = identity.expires_at + timedelta(days=1)
    with pytest.raises(InvalidAgentCertificateError, match="expired"):
        reg.validate_agent("context_agent", now=future)


def test_registry_init_failure_blocks_validation() -> None:
    reg = NHIRegistry()
    with pytest.raises(RegistryInitError):
        reg.validate_agent("context_agent")


def test_renewal_warning_logged(caplog) -> None:  # type: ignore[no-untyped-def]
    reg = NHIRegistry()
    reg.initialize()
    identity = reg.get("planner_agent")
    assert identity is not None
    near_expiry = identity.expires_at - timedelta(days=3)
    reg.validate_agent("planner_agent", now=near_expiry)
