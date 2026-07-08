"""OpenTelemetry configuration.

TF-011 baseline:
- Configure a TracerProvider on startup.
- If the OTLP endpoint is unreachable: warn and continue without export.
- Provide `get_tracer()` for consistent span creation.
"""

from __future__ import annotations

import logging
import socket
from urllib.parse import urlparse

from opentelemetry.trace import Tracer

from backend.settings import Settings

logger = logging.getLogger(__name__)


def _otlp_endpoint_is_reachable(endpoint: str, *, timeout_seconds: float = 0.8) -> bool:
    """Best-effort TCP reachability check for the OTLP host/port."""
    try:
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4317
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except Exception:
        return False


def configure_opentelemetry(settings: Settings) -> None:
    """Configure OpenTelemetry span export (optional) and tracer provider."""
    # Always configure a TracerProvider so spans + trace_id context work even if export is disabled.
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": "taskflow-ai"})
    provider = TracerProvider(resource=resource)

    endpoint = settings.otel_exporter_otlp_endpoint
    if endpoint:
        try:
            if _otlp_endpoint_is_reachable(endpoint):
                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
            else:
                logger.warning(
                    "otel_exporter_unreachable",
                    extra={"endpoint": endpoint},
                )
        except Exception:
            logger.warning(
                "otel_exporter_configuration_failed",
                extra={"endpoint": endpoint},
            )

    trace.set_tracer_provider(provider)


def get_tracer() -> Tracer:
    """Return a tracer for creating spans."""
    from opentelemetry import trace

    return trace.get_tracer("taskflow-ai")


def configure_telemetry(settings: Settings) -> None:
    """Backward-compatible entrypoint for TF-011."""
    configure_opentelemetry(settings)
