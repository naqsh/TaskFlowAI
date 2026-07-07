"""Spotlighting utility tests."""

from backend.security.spotlighting import (
    EXTERNAL_MARKER_END,
    EXTERNAL_MARKER_START,
    spotlight_external_content,
)


def test_spotlight_wraps_content() -> None:
    result = spotlight_external_content("Buy milk")
    assert EXTERNAL_MARKER_START in result
    assert EXTERNAL_MARKER_END in result
    assert "Buy milk" in result


def test_spotlight_empty_content() -> None:
    result = spotlight_external_content("")
    assert result.startswith(EXTERNAL_MARKER_START)
    assert result.endswith(EXTERNAL_MARKER_END)
