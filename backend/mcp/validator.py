from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import nh3
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.db.models import TaskPriority
from backend.kernel.errors import MCPValidationError
from backend.kernel.security_monitor import SecurityMonitor
from backend.logging_config import get_logger

logger = get_logger(__name__)

_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)
_DEFAULT_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "taskflow.ai", "www.taskflow.ai"})


class TaskMcpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    title: str
    description: str | None = None
    priority: TaskPriority | str
    due_date: date | None = None


class ProjectMcpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None


class CommentMcpItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: UUID
    workspace_id: UUID
    task_id: UUID
    body: str


class MCPResponseValidator:
    """Three-layer MCP defense: schema, sanitization, anomaly (TF-042)."""

    def __init__(
        self,
        *,
        security_monitor: SecurityMonitor | None = None,
        allowed_url_hosts: frozenset[str] | None = None,
        default_size_threshold: int = 50_000,
        anomaly_sigma: float = 2.0,
        quarantine_writer: object | None = None,
    ) -> None:
        self._monitor = security_monitor or SecurityMonitor()
        self._allowed_hosts = allowed_url_hosts or _DEFAULT_ALLOWED_HOSTS
        self._default_size_threshold = default_size_threshold
        self._anomaly_sigma = anomaly_sigma
        self._quarantine_writer = quarantine_writer

    def validate(
        self,
        tool: str,
        response: Any,
        *,
        latency_ms: float = 0.0,
    ) -> Any:
        raw_size = len(json.dumps(response, default=str).encode("utf-8"))
        anomaly = self._monitor.record_mcp_response(
            tool,
            response_size=raw_size,
            latency_ms=latency_ms,
            default_size_threshold=self._default_size_threshold,
            default_sigma=self._anomaly_sigma,
        )

        try:
            validated = self._validate_schema(tool, response)
            sanitized = self._sanitize_response(validated)
            self._check_urls(sanitized)
        except ValidationError:
            raise
        except ValueError as e:
            raise MCPValidationError(f"mcp_validation_failed tool={tool}") from e

        if anomaly or raw_size > self._default_size_threshold * 10:
            self._quarantine(tool, response, reason="size_anomaly")
            raise MCPValidationError(f"mcp_response_quarantined tool={tool}")

        return sanitized

    def _validate_schema(self, tool: str, response: Any) -> Any:
        if tool == "tasks.list":
            return self._validate_list(response, model=TaskMcpItem)
        if tool == "projects.list":
            return self._validate_list(response, model=ProjectMcpItem)
        if tool == "comments.list":
            return self._validate_list(response, model=CommentMcpItem)
        return response

    @staticmethod
    def _validate_list(response: Any, *, model: type[BaseModel]) -> list[dict[str, Any]]:
        if response is None:
            return []
        if not isinstance(response, list):
            raise ValueError("expected list response from MCP")

        validated = [model.model_validate(item) for item in response]
        return [v.model_dump() for v in validated]

    def _sanitize_response(self, response: Any) -> Any:
        if isinstance(response, list):
            return [self._sanitize_item(item) for item in response]
        if isinstance(response, dict):
            return self._sanitize_item(response)
        return response

    def _sanitize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in item.items():
            if isinstance(value, str):
                out[key] = nh3.clean(value)
            elif isinstance(value, datetime):
                out[key] = value.astimezone(UTC).isoformat()
            elif isinstance(value, date):
                out[key] = value.isoformat()
            else:
                out[key] = value
        return out

    def _check_urls(self, response: Any) -> None:
        text = json.dumps(response, default=str)
        for match in _URL_PATTERN.finditer(text):
            url = match.group(0)
            host = urlparse(url).hostname
            if host is None:
                continue
            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback:
                    raise MCPValidationError(f"internal_url_blocked host={host}")
            except ValueError:
                pass
            if host not in self._allowed_hosts:
                raise MCPValidationError(f"url_not_allowlisted host={host}")

    def _quarantine(self, tool: str, response: Any, *, reason: str) -> None:
        raw = json.dumps(response, default=str)
        raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if self._quarantine_writer is None:
            logger.warning("mcp_quarantine_no_writer", tool=tool, reason=reason, raw_hash=raw_hash)
            return
        try:
            self._quarantine_writer.write(  # type: ignore[attr-defined]
                tool=tool,
                reason=reason,
                raw_hash=raw_hash,
            )
        except Exception:
            logger.error("mcp_quarantine_write_failed", tool=tool)
            raise MCPValidationError(f"mcp_quarantine_failed tool={tool}") from None
