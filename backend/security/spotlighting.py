"""Zero-trust spotlighting for external user-generated content."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

EXTERNAL_MARKER_START = "<<<EXTERNAL_CONTENT>>>"
EXTERNAL_MARKER_END = "<<</EXTERNAL_CONTENT>>>"

_STRIPPED_START = EXTERNAL_MARKER_START.rstrip()
_STRIPPED_END = EXTERNAL_MARKER_END.rstrip()


def is_spotlighted(content: str) -> bool:
    """Return True if `content` is already wrapped in spotlighting markers."""
    if not content:
        return False
    stripped = content.strip()
    return stripped.startswith(_STRIPPED_START) and stripped.endswith(_STRIPPED_END)


def _spotlight_text(content: str) -> str:
    # Internal helper that assumes content != "".
    if is_spotlighted(content):
        return content
    return f"{EXTERNAL_MARKER_START}\n{content}\n{EXTERNAL_MARKER_END}"


def spotlight_external_content(content: str) -> str:
    """Wrap untrusted content in spotlighting markers for LLM consumption."""
    if content == "":
        # Edge case: empty strings are informationally empty.
        return ""
    return _spotlight_text(content)


def spotlight_dict(data: dict[str, Any], text_fields: Iterable[str]) -> dict[str, Any]:
    """Spotlight selected string fields inside a payload.

    - Non-string fields are left untouched.
    - Already spotlighted values are not wrapped again.
    """

    out: dict[str, Any] = deepcopy(data)
    for field in text_fields:
        if field not in out:
            continue

        value = out[field]
        if isinstance(value, str):
            out[field] = spotlight_external_content(value)
        elif isinstance(value, list) and all(isinstance(v, str) for v in value):
            out[field] = [spotlight_external_content(v) for v in value]
    return out
