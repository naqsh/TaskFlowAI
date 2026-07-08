"""Spotlighting utility tests."""

from backend.security.spotlighting import (
    EXTERNAL_MARKER_END,
    EXTERNAL_MARKER_START,
    is_spotlighted,
    spotlight_dict,
    spotlight_external_content,
)


def test_spotlight_wraps_content() -> None:
    result = spotlight_external_content("Buy milk")
    assert EXTERNAL_MARKER_START in result
    assert EXTERNAL_MARKER_END in result
    assert "Buy milk" in result


def test_spotlight_empty_content() -> None:
    result = spotlight_external_content("")
    assert result == ""


def test_spotlight_dict_wraps_selected_fields() -> None:
    payload = {"title": "Buy milk", "other": "Keep me"}
    result = spotlight_dict(payload, text_fields=["title"])
    assert "<<<EXTERNAL_CONTENT>>>" in result["title"]
    assert result["other"] == "Keep me"


def test_is_spotlighted_prevents_double_wrapping() -> None:
    once = spotlight_external_content("Buy milk")
    twice = spotlight_external_content(once)
    assert once == twice
    assert is_spotlighted(twice)
