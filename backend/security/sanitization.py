"""HTML sanitization for user-generated content."""

from __future__ import annotations

import nh3


def sanitize_description(text: str | None) -> str | None:
    """Strip unsafe HTML from free-text descriptions."""
    if text is None:
        return None
    cleaned = nh3.clean(text)
    return cleaned if cleaned else None
