"""Identity component factories (TF-E5)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.kernel.identity_manager import IdentityManager
from backend.security.audit_seal import AuditLogWriter
from backend.security.nhi_registry import NHIRegistry, nhi_registry
from backend.security.vault import CredentialBroker
from backend.services.consent_service import ConsentService
from backend.settings import Settings


class VaultAuditBridge:
    """Bridge CredentialBroker audit events to sealed audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self._writer = AuditLogWriter(session)

    async def append_credential_issued(
        self,
        *,
        user_id: UUID,
        service: str,
        intent: str,
        workspace_id: UUID | None = None,
    ) -> None:
        await self._writer.append(
            actor_id=user_id,
            action="credential.issued",
            resource_type="credential",
            resource_id=None,
            workspace_id=workspace_id,
            metadata={"service": service, "intent": intent},
        )


def build_identity_manager(settings: Settings) -> IdentityManager:
    return IdentityManager(grace_seconds=settings.delegation_grace_seconds)


def build_credential_broker(
    settings: Settings,
    *,
    session: AsyncSession | None = None,
) -> CredentialBroker:
    audit = VaultAuditBridge(session) if session is not None else None
    return CredentialBroker(
        mode=settings.vault_mode,
        supabase_anon_key=settings.supabase_anon_key,
        audit=audit,
    )


def get_nhi_registry() -> NHIRegistry:
    return nhi_registry


def build_consent_service(session: AsyncSession) -> ConsentService:
    return ConsentService(session)
