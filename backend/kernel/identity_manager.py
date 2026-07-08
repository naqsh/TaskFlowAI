from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

DelegationIntent = Literal[
    "read_tasks",
    "read_projects",
    "read_comments",
    "create_task",
    "update_task",
    "none",
]


@dataclass(frozen=True)
class DelegationContext:
    """Stub delegation context used for confused-deputy prevention (MVP Part 1)."""

    user_id: UUID
    session_id: str
    agent_id: str
    intent: DelegationIntent
    permissions: list[str]
    issued_at: datetime
    expires_at: datetime
    parent_trace_id: str | None = None

    @staticmethod
    def default_for(user_id: UUID, agent_id: str, intent: DelegationIntent) -> DelegationContext:
        now = datetime.now(UTC)
        # 15 minutes default TTL as specified in the proposal.
        return DelegationContext(
            user_id=user_id,
            session_id="stub",
            agent_id=agent_id,
            intent=intent,
            permissions=[],
            issued_at=now,
            expires_at=now.replace(minute=now.minute + 15),
            parent_trace_id=None,
        )


class IdentityManager:
    """Identity + delegation scaffolds (Part 1 stub)."""

    async def create_delegation_context(
        self, user_id: UUID, agent_id: str, intent: DelegationIntent
    ) -> Any:
        # Part 1 uses a stub; Part 5 replaces it with Vault-backed JIT issuance.
        return DelegationContext.default_for(user_id=user_id, agent_id=agent_id, intent=intent)
