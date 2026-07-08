from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AuditLog
from backend.logging_config import get_logger
from backend.metrics import AUDIT_CHAIN_VERIFICATION_FAILURES_TOTAL

logger = get_logger(__name__)

GENESIS_PREV_HASH = "0" * 64
_MAX_PAYLOAD_BYTES = 10_240


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_entry_hash(prev_hash: str, payload: dict[str, Any]) -> str:
    canonical = _canonical_json(payload)
    return _sha256_hex(f"{prev_hash}{canonical}")


class AuditLogWriter:
    """Hash-chain sealed audit log writer (TF-046)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict[str, Any] | None = None,
        workspace_id: UUID | None = None,
    ) -> AuditLog | None:
        try:
            prev_hash = await self._latest_hash()
            sanitized = self._sanitize_payload(metadata or {})
            entry_hash = compute_entry_hash(prev_hash, sanitized)

            entry = AuditLog(
                workspace_id=workspace_id,
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata_=sanitized,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
            self._session.add(entry)
            await self._session.flush()
            return entry
        except Exception:
            logger.error("audit_seal_write_failed", action=action)
            return None

    async def _latest_hash(self) -> str:
        stmt = (
            select(AuditLog.entry_hash)
            .where(AuditLog.entry_hash.is_not(None))
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        latest = result.scalar_one_or_none()
        return latest if latest else GENESIS_PREV_HASH

    @staticmethod
    def _sanitize_payload(metadata: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(metadata, default=str)
        if len(raw.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            return {"payload_sha256": _sha256_hex(raw)}
        out: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, str) and len(value) > 256:
                out[f"{key}_sha256"] = _sha256_hex(value)
            else:
                out[key] = value
        return out


async def verify_audit_chain(session: AsyncSession) -> bool:
    """Verify hash-chain integrity; return False if tampered."""
    stmt = select(AuditLog).where(AuditLog.entry_hash.is_not(None)).order_by(AuditLog.created_at)
    result = await session.execute(stmt)
    entries = list(result.scalars().all())
    if not entries:
        return True

    expected_prev = GENESIS_PREV_HASH
    for entry in entries:
        if entry.prev_hash != expected_prev:
            AUDIT_CHAIN_VERIFICATION_FAILURES_TOTAL.inc()
            return False
        computed = compute_entry_hash(expected_prev, entry.metadata_)
        if computed != entry.entry_hash:
            AUDIT_CHAIN_VERIFICATION_FAILURES_TOTAL.inc()
            return False
        expected_prev = entry.entry_hash
    return True
