"""JIT credential broker for MCP clients (TF-050)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID

from backend.metrics import CREDENTIAL_ISSUANCE_TOTAL

VaultMode = Literal["memory", "env"]


class CredentialDeniedError(Exception):
    """Raised when consent or policy denies credential issuance."""


class BrokerUnavailableError(Exception):
    """Raised when the credential broker cannot issue credentials."""


@dataclass(frozen=True)
class Credential:
    """Short-lived credential scoped to user, service, and intent."""

    user_id: UUID
    service: str
    intent: str
    access_token: str
    issued_at: datetime
    expires_at: datetime
    from_cache: bool = False


class ConsentChecker(Protocol):
    async def has_consent(self, user_id: UUID, workspace_id: UUID) -> bool: ...


class AuditAppender(Protocol):
    async def append_credential_issued(
        self,
        *,
        user_id: UUID,
        service: str,
        intent: str,
        workspace_id: UUID | None = None,
    ) -> None: ...


class _NullAuditAppender:
    async def append_credential_issued(
        self,
        *,
        user_id: UUID,
        service: str,
        intent: str,
        workspace_id: UUID | None = None,
    ) -> None:
        _ = (user_id, service, intent, workspace_id)


class CredentialBroker:
    """Issue short-lived credentials for MCP tool access (TTL ≤ 900s)."""

    _SUPPORTED_SERVICES = frozenset({"supabase"})
    _SUPPORTED_INTENTS = frozenset({"read_tasks", "read_projects", "update_tasks", "read_comments"})

    def __init__(
        self,
        *,
        mode: VaultMode = "memory",
        supabase_anon_key: str = "",
        audit: AuditAppender | None = None,
    ) -> None:
        self._mode = mode
        self._supabase_anon_key = supabase_anon_key
        self._audit = audit or _NullAuditAppender()
        self._cache: dict[str, Credential] = {}

    @staticmethod
    def _cache_key(user_id: UUID, service: str, intent: str) -> str:
        return f"{user_id}:{service}:{intent}"

    async def get_credential(
        self,
        *,
        user_id: UUID,
        service: str,
        intent: str,
        workspace_id: UUID | None = None,
        ttl_seconds: int = 900,
        consent_checker: ConsentChecker | None = None,
    ) -> Credential:
        """Issue or return cached credential after consent validation."""
        if ttl_seconds <= 0:
            msg = "ttl_seconds must be > 0"
            raise ValueError(msg)
        if service not in self._SUPPORTED_SERVICES:
            raise CredentialDeniedError(f"unsupported_service service={service}")
        if intent not in self._SUPPORTED_INTENTS:
            raise CredentialDeniedError(f"unsupported_intent intent={intent}")

        if consent_checker is not None and workspace_id is not None:
            if not await consent_checker.has_consent(user_id, workspace_id):
                raise CredentialDeniedError("consent_required")

        cache_key = self._cache_key(user_id, service, intent)
        cached = self._cache.get(cache_key)
        now = datetime.now(UTC)
        if cached is not None and cached.expires_at > now:
            return Credential(
                user_id=cached.user_id,
                service=cached.service,
                intent=cached.intent,
                access_token=cached.access_token,
                issued_at=cached.issued_at,
                expires_at=cached.expires_at,
                from_cache=True,
            )

        token = self._resolve_token(service)
        if not token:
            raise BrokerUnavailableError("broker_unavailable")

        clamped_ttl = min(ttl_seconds, 900)
        credential = Credential(
            user_id=user_id,
            service=service,
            intent=intent,
            access_token=token,
            issued_at=now,
            expires_at=now + timedelta(seconds=clamped_ttl),
        )
        self._cache[cache_key] = credential
        CREDENTIAL_ISSUANCE_TOTAL.labels(service=service, intent=intent).inc()
        await self._audit.append_credential_issued(
            user_id=user_id,
            service=service,
            intent=intent,
            workspace_id=workspace_id,
        )
        return credential

    def _resolve_token(self, service: str) -> str:
        if service == "supabase":
            if self._mode == "env" and self._supabase_anon_key:
                return self._supabase_anon_key
            if self._mode == "memory":
                return f"jit-{secrets.token_urlsafe(24)}"
        return ""
