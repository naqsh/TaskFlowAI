"""Tests for JIT CredentialBroker (TF-050)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.security.vault import (
    BrokerUnavailableError,
    CredentialBroker,
    CredentialDeniedError,
)


class _AllowConsent:
    async def has_consent(self, user_id, workspace_id) -> bool:  # type: ignore[no-untyped-def]
        _ = (user_id, workspace_id)
        return True


class _DenyConsent:
    async def has_consent(self, user_id, workspace_id) -> bool:  # type: ignore[no-untyped-def]
        _ = (user_id, workspace_id)
        return False


@pytest.mark.asyncio
async def test_issued_credential_expires_within_ttl() -> None:
    broker = CredentialBroker(mode="memory")
    cred = await broker.get_credential(
        user_id=uuid4(),
        service="supabase",
        intent="read_tasks",
        ttl_seconds=300,
        consent_checker=_AllowConsent(),
        workspace_id=uuid4(),
    )
    delta = cred.expires_at - cred.issued_at
    assert delta.total_seconds() <= 300


@pytest.mark.asyncio
async def test_missing_consent_raises() -> None:
    broker = CredentialBroker(mode="memory")
    with pytest.raises(CredentialDeniedError, match="consent_required"):
        await broker.get_credential(
            user_id=uuid4(),
            service="supabase",
            intent="read_tasks",
            consent_checker=_DenyConsent(),
            workspace_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_cache_hit_within_ttl_no_double_issue() -> None:
    broker = CredentialBroker(mode="memory")
    user_id = uuid4()
    ws_id = uuid4()
    first = await broker.get_credential(
        user_id=user_id,
        service="supabase",
        intent="read_tasks",
        consent_checker=_AllowConsent(),
        workspace_id=ws_id,
    )
    second = await broker.get_credential(
        user_id=user_id,
        service="supabase",
        intent="read_tasks",
        consent_checker=_AllowConsent(),
        workspace_id=ws_id,
    )
    assert first.access_token == second.access_token
    assert second.from_cache is True


@pytest.mark.asyncio
async def test_ttl_zero_raises() -> None:
    broker = CredentialBroker(mode="memory")
    with pytest.raises(ValueError):
        await broker.get_credential(
            user_id=uuid4(),
            service="supabase",
            intent="read_tasks",
            ttl_seconds=0,
        )


@pytest.mark.asyncio
async def test_broker_unavailable_in_env_mode_without_key() -> None:
    broker = CredentialBroker(mode="env", supabase_anon_key="")
    with pytest.raises(BrokerUnavailableError):
        await broker.get_credential(
            user_id=uuid4(),
            service="supabase",
            intent="read_tasks",
            consent_checker=_AllowConsent(),
            workspace_id=uuid4(),
        )
