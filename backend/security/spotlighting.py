"""Zero-trust spotlighting for external user-generated content."""

EXTERNAL_MARKER_START = "<<<EXTERNAL_CONTENT>>>"
EXTERNAL_MARKER_END = "<<<END_EXTERNAL_CONTENT>>>"


def spotlight_external_content(content: str) -> str:
    """Wrap untrusted content in spotlighting markers for LLM consumption."""
    return f"{EXTERNAL_MARKER_START}\n{content}\n{EXTERNAL_MARKER_END}"
