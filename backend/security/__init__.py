"""Security utilities."""

from backend.security.input_scanner import InputSecurityScanner, ScanResult, SecurityViolationError
from backend.security.spotlighting import (
    EXTERNAL_MARKER_END,
    EXTERNAL_MARKER_START,
    is_spotlighted,
    spotlight_dict,
    spotlight_external_content,
)

__all__ = [
    "EXTERNAL_MARKER_END",
    "EXTERNAL_MARKER_START",
    "is_spotlighted",
    "spotlight_external_content",
    "spotlight_dict",
    "InputSecurityScanner",
    "ScanResult",
    "SecurityViolationError",
]
