"""OpenTelemetry configuration."""

from __future__ import annotations

import logging

from backend.settings import Settings

logger = logging.getLogger(__name__)


def configure_telemetry(settings: Settings) -> None:
    """Configure OpenTelemetry exporters when endpoint is reachable."""
    if not settings.otel_exporter_otlp_endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "taskflow-ai"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    except Exception:
        logger.warning(
            "otel_configuration_failed",
            extra={"endpoint": settings.otel_exporter_otlp_endpoint},
        )
