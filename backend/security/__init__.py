"""Security utilities."""

from backend.security.spotlighting import (
    EXTERNAL_MARKER_END,
    EXTERNAL_MARKER_START,
    spotlight_external_content,
)

__all__ = [
    "EXTERNAL_MARKER_END",
    "EXTERNAL_MARKER_START",
    "spotlight_external_content",
]
