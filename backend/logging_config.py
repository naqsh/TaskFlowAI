"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator, MutableMapping
from typing import Any
from uuid import uuid4

import structlog


def _ensure_trace_id(
    _logger: Any,
    _method: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    if "trace_id" not in event_dict:
        event_dict["trace_id"] = uuid4().hex
        event_dict["trace_id_generated"] = True
    return event_dict


def configure_logging(*, debug: bool = False) -> None:
    """Configure structlog for JSON output with trace_id support."""
    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _ensure_trace_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_trace_id(trace_id: str) -> None:
    """Bind trace_id to the current structlog context."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(trace_id=trace_id)


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger."""
    return structlog.get_logger(name)
