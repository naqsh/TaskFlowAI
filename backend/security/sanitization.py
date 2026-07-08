"""HTML sanitization for user-generated content."""

from __future__ import annotations

import nh3

COMMENT_ALLOWED_TAGS: frozenset[str] = frozenset({"p", "br", "strong", "em", "code"})


def sanitize_description(text: str | None) -> str | None:
    """Strip unsafe HTML from free-text descriptions."""
    if text is None:
        return None
    cleaned = nh3.clean(text)
    return cleaned if cleaned else None


def sanitize_comment_body(text: str) -> str:
    """Sanitize comment HTML allowing a small safe tag subset."""
    cleaned = nh3.clean(text, tags=COMMENT_ALLOWED_TAGS)
    return cleaned.strip()
