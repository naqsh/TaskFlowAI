"""Non-Human Identity (NHI) X.509 agent registry (TF-052)."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.logging_config import get_logger

logger = get_logger(__name__)

CERT_VALIDITY_DAYS = 7
RENEWAL_WARNING_DAYS = 7

AGENT_ALLOWLIST: dict[str, dict[str, Any]] = {
    "context_agent": {
        "canonical_role": "tool_operator",
        "permissions": ["tasks:read", "projects:read", "comments:read"],
        "blast_radius": "medium",
    },
    "planner_agent": {
        "canonical_role": "planner",
        "permissions": ["tasks:read"],
        "blast_radius": "low",
    },
    "verification_agent": {
        "canonical_role": "verifier",
        "permissions": ["tasks:read"],
        "blast_radius": "low",
    },
    "adversarial_agent": {
        "canonical_role": "adversary",
        "permissions": ["tasks:read"],
        "blast_radius": "low",
    },
    "critic_agent": {
        "canonical_role": "critic",
        "permissions": ["tasks:read"],
        "blast_radius": "low",
    },
    "orchestrator_agent": {
        "canonical_role": "presenter",
        "permissions": ["tasks:read"],
        "blast_radius": "minimal",
    },
}

GLOBAL_PERMISSION_ALLOWLIST = frozenset(
    {
        "tasks:read",
        "tasks:create",
        "tasks:update",
        "projects:read",
        "comments:read",
    }
)


class NHIRegistryError(Exception):
    """Base NHI registry error."""


class DuplicateAgentError(NHIRegistryError):
    """Raised when registering an agent_id that already exists."""


class PermissionExceedsAllowlistError(NHIRegistryError):
    """Raised when certificate permissions exceed the global allowlist."""


class InvalidAgentCertificateError(NHIRegistryError):
    """Raised when an agent certificate fails validation."""


class RegistryInitError(NHIRegistryError):
    """Raised when registry initialization fails (fail secure)."""


@dataclass(frozen=True)
class AgentIdentity:
    """X.509-style agent identity (dev: self-signed stub)."""

    agent_id: str
    canonical_role: str
    permissions: list[str]
    issued_at: datetime
    expires_at: datetime
    certificate_pem: str
    metadata: dict[str, Any] = field(default_factory=dict)
    revoked: bool = False


class NHIRegistry:
    """In-memory NHI registry with self-signed dev certificates."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentIdentity] = {}
        self._revoked_serials: set[str] = set()
        self._initialized = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> None:
        """Register all 6 agents on startup if not present."""
        if self._initialized:
            return
        try:
            for agent_id, spec in AGENT_ALLOWLIST.items():
                if agent_id not in self._agents:
                    self.register_agent(
                        agent_id=agent_id,
                        canonical_role=spec["canonical_role"],
                        permissions=spec["permissions"],
                        metadata={"blast_radius": spec["blast_radius"]},
                    )
            self._initialized = True
            logger.info("nhi_registry_initialized", agent_count=len(self._agents))
        except Exception as exc:
            self._initialized = False
            raise RegistryInitError(str(exc)) from exc

    def register_agent(
        self,
        *,
        agent_id: str,
        canonical_role: str,
        permissions: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> AgentIdentity:
        if agent_id in self._agents:
            raise DuplicateAgentError(f"duplicate_agent_id agent_id={agent_id}")
        for perm in permissions:
            if perm not in GLOBAL_PERMISSION_ALLOWLIST:
                raise PermissionExceedsAllowlistError(
                    f"permission_exceeds_allowlist permission={perm}"
                )

        now = datetime.now(UTC)
        expires = now + timedelta(days=CERT_VALIDITY_DAYS)
        cert_pem = self._generate_self_signed_cert(agent_id, canonical_role, now, expires)
        identity = AgentIdentity(
            agent_id=agent_id,
            canonical_role=canonical_role,
            permissions=list(permissions),
            issued_at=now,
            expires_at=expires,
            certificate_pem=cert_pem,
            metadata=metadata or {},
        )
        self._agents[agent_id] = identity
        self._check_renewal_warning(identity)
        return identity

    def get(self, agent_id: str) -> AgentIdentity | None:
        return self._agents.get(agent_id)

    def validate_agent(self, agent_id: str, *, now: datetime | None = None) -> AgentIdentity:
        """Validate agent certificate before MCP invocation."""
        if not self._initialized:
            raise RegistryInitError("registry_not_initialized")
        identity = self._agents.get(agent_id)
        if identity is None:
            raise InvalidAgentCertificateError(f"unknown_agent agent_id={agent_id}")
        if identity.revoked or identity.certificate_pem in self._revoked_serials:
            raise InvalidAgentCertificateError(f"revoked_cert agent_id={agent_id}")
        current = now or datetime.now(UTC)
        if current > identity.expires_at:
            raise InvalidAgentCertificateError(f"expired_cert agent_id={agent_id}")
        self._check_renewal_warning(identity, now=current)
        return identity

    def revoke(self, agent_id: str) -> None:
        identity = self._agents.get(agent_id)
        if identity is None:
            return
        self._revoked_serials.add(identity.certificate_pem)
        self._agents[agent_id] = AgentIdentity(
            agent_id=identity.agent_id,
            canonical_role=identity.canonical_role,
            permissions=identity.permissions,
            issued_at=identity.issued_at,
            expires_at=identity.expires_at,
            certificate_pem=identity.certificate_pem,
            metadata=identity.metadata,
            revoked=True,
        )

    def list_agents(self) -> list[AgentIdentity]:
        return list(self._agents.values())

    @staticmethod
    def _generate_self_signed_cert(
        agent_id: str,
        canonical_role: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> str:
        """Dev stub: deterministic PEM-like token (prod: Vault PKI)."""
        payload = f"{agent_id}:{canonical_role}:{issued_at.isoformat()}:{expires_at.isoformat()}"
        digest = hashlib.sha256(payload.encode()).hexdigest()
        nonce = secrets.token_hex(8)
        return (
            f"-----BEGIN CERTIFICATE-----\n"
            f"CN={agent_id};ROLE={canonical_role};SERIAL={digest[:16]};NONCE={nonce}\n"
            f"-----END CERTIFICATE-----"
        )

    def _check_renewal_warning(
        self, identity: AgentIdentity, *, now: datetime | None = None
    ) -> None:
        current = now or datetime.now(UTC)
        days_left = (identity.expires_at - current).days
        if days_left <= RENEWAL_WARNING_DAYS:
            logger.warning(
                "nhi_cert_renewal_warning",
                agent_id=identity.agent_id,
                days_remaining=days_left,
            )


# Module-level singleton for app lifespan.
nhi_registry = NHIRegistry()
