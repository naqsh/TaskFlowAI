"""Security component factories wired from application settings (TF-E4)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.kernel.security_monitor import SecurityMonitor
from backend.mcp.quarantine import QuarantineWriter
from backend.mcp.validator import MCPResponseValidator
from backend.security.input_scanner import InputSecurityScanner
from backend.settings import Settings


def build_input_scanner(settings: Settings) -> InputSecurityScanner:
    """Create InputSecurityScanner from runtime settings."""
    return InputSecurityScanner(
        llamafirewall_enabled=settings.llamafirewall_enabled,
        block_threshold=settings.llamafirewall_block_threshold,
        hf_token=settings.hf_token or None,
        app_env=settings.app_env,
    )


def build_security_monitor(settings: Settings) -> SecurityMonitor:
    """Create SecurityMonitor from runtime settings."""
    return SecurityMonitor(enabled=settings.security_monitor_enabled)


def build_mcp_validator(
    settings: Settings,
    *,
    security_monitor: SecurityMonitor | None = None,
    session: AsyncSession | None = None,
) -> MCPResponseValidator:
    """Create MCPResponseValidator with optional quarantine persistence."""
    monitor = security_monitor or build_security_monitor(settings)
    quarantine_writer = QuarantineWriter(session) if session is not None else None
    return MCPResponseValidator(
        security_monitor=monitor,
        default_size_threshold=settings.mcp_default_size_threshold,
        anomaly_sigma=settings.mcp_anomaly_sigma,
        quarantine_writer=quarantine_writer,
    )
