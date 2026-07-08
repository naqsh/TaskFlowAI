"""Sanitization utility tests."""

from backend.security.sanitization import sanitize_description


def test_sanitize_description_strips_script_tags() -> None:
    raw = '<p>Hello</p><script>alert("xss")</script>'
    cleaned = sanitize_description(raw)
    assert cleaned is not None
    assert "<script>" not in cleaned
    assert "alert" not in cleaned


def test_sanitize_description_none_passthrough() -> None:
    assert sanitize_description(None) is None


def test_sanitize_comment_body_strips_script() -> None:
    from backend.security.sanitization import sanitize_comment_body

    cleaned = sanitize_comment_body("<script>alert(1)</script>safe")
    assert "<script>" not in cleaned
