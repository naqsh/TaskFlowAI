"""Audit logging service (append-only).

TF-011 acceptance highlights:
- `log_event(...)` persists an `audit_logs` row.
- Audit write failures do not fail the request.
- Metadata is sanitized to avoid storing raw PII.
- Metadata includes trace correlation (OTel trace_id when available).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from backend.db.models import AuditLog
from backend.db.session import get_session_factory
from backend.logging_config import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

# Keys commonly used to carry PII / secrets in request payloads.
_SENSITIVE_METADATA_KEYS = {
    "email",
    "password",
    "token",
    "refresh_token",
    "authorization",
    "body",
    "content",
    "description",
    "title",
    "full_name",
}


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sanitize_metadata(value: Any) -> Any:
    """Sanitize potentially sensitive metadata values recursively.

    Rule: if a dict key is sensitive OR a string value looks like email, hash it.
    """

    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = str(k)
            if isinstance(v, str) and (
                key.lower() in _SENSITIVE_METADATA_KEYS or _EMAIL_RE.search(v)
            ):
                out[f"{key}_sha256"] = _sha256_hex(v)
            else:
                out[key] = _sanitize_metadata(v)
        return out

    if isinstance(value, list):
        return [_sanitize_metadata(v) for v in value]

    # Only transform strings when a surrounding dict key indicates sensitivity.
    return value


class AuditService:
    """Append-only audit log writer."""

    def __init__(self) -> None:
        self._session_factory = get_session_factory()

    async def log_event(
        self,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict[str, Any] | None = None,
        *,
        workspace_id: UUID | None = None,
    ) -> None:
        """Persist an audit event.

        Fail-closed for security, fail-open for request health: never raise.
        """

        sanitized: dict[str, Any] = {}
        if metadata:
            sanitized = _sanitize_metadata(metadata)

        # Attach trace_id for request correlation (if a span exists).
        try:
            from opentelemetry import trace as otel_trace

            span_ctx = otel_trace.get_current_span().get_span_context()
            if span_ctx is not None and span_ctx.trace_id:
                sanitized.setdefault("trace_id", f"{span_ctx.trace_id:032x}")
        except Exception:
            # Correlation is best-effort only.
            pass

        entry = AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=sanitized,
        )

        try:
            async with self._session_factory() as session:
                session.add(entry)
                await session.commit()
        except Exception:
            logger.error(
                "audit_log_write_failed",
                extra={"action": action, "resource_type": resource_type},
            )
