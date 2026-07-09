from __future__ import annotations

from typing import Any
from uuid import UUID

from backend.security.delegation import (
    DelegationContext,
    DelegationIntent,
    create_delegation,
    validate_delegation,
)


class IdentityManager:
    """Identity + delegation issuance and validation (TF-049)."""

    def __init__(self, *, grace_seconds: int = 30) -> None:
        self._grace_seconds = grace_seconds
        self._revoked_sessions: set[str] = set()

    def revoke_session(self, session_id: str) -> None:
        self._revoked_sessions.add(session_id)

    def is_session_revoked(self, session_id: str) -> bool:
        return session_id in self._revoked_sessions

    async def create_delegation_context(
        self,
        user_id: UUID,
        agent_id: str,
        intent: DelegationIntent,
        *,
        session_id: str,
        parent_trace_id: str | None = None,
        ttl_seconds: int = 900,
    ) -> DelegationContext:
        ctx = create_delegation(
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            intent=intent,
            parent_trace_id=parent_trace_id,
            ttl_seconds=ttl_seconds,
            grace_seconds=self._grace_seconds,
        )
        if self.is_session_revoked(session_id):
            return DelegationContext(
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                agent_id=ctx.agent_id,
                intent=ctx.intent,
                permissions=ctx.permissions,
                issued_at=ctx.issued_at,
                expires_at=ctx.expires_at,
                parent_trace_id=ctx.parent_trace_id,
                revoked=True,
            )
        return ctx

    def validate_delegation_context(
        self,
        ctx: DelegationContext,
        *,
        tool: str | None = None,
        required_permission: str | None = None,
    ) -> None:
        if self.is_session_revoked(ctx.session_id):
            from backend.security.delegation import DelegationRevokedError

            raise DelegationRevokedError("session_revoked")
        validate_delegation(
            ctx,
            tool=tool,
            required_permission=required_permission,
            grace_seconds=self._grace_seconds,
        )

    def delegation_for_mcp(
        self,
        ctx: DelegationContext,
        tool: str,
    ) -> DelegationContext:
        """Validate delegation before MCP call; raises on confused deputy."""
        self.validate_delegation_context(ctx, tool=tool)
        return ctx

    @staticmethod
    def serialize(ctx: DelegationContext) -> dict[str, Any]:
        return {
            "user_id": str(ctx.user_id),
            "session_id": ctx.session_id,
            "agent_id": ctx.agent_id,
            "intent": ctx.intent,
            "permissions": list(ctx.permissions),
            "issued_at": ctx.issued_at.isoformat(),
            "expires_at": ctx.expires_at.isoformat(),
            "parent_trace_id": ctx.parent_trace_id,
            "revoked": ctx.revoked,
        }

    @staticmethod
    def default_for(
        user_id: UUID,
        agent_id: str,
        intent: DelegationIntent,
        *,
        session_id: str = "stub",
        parent_trace_id: str | None = None,
    ) -> DelegationContext:
        """Backward-compatible helper for tests."""
        return create_delegation(
            user_id=user_id,
            session_id=session_id,
            agent_id=agent_id,
            intent=intent,
            parent_trace_id=parent_trace_id,
        )
