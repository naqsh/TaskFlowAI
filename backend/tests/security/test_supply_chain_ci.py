"""Supply chain CI policy constants and documentation gates (TF-056)."""

from __future__ import annotations

from pathlib import Path

OPENSSF_SCORECARD_MIN = 7.0
PIP_AUDIT_FAIL_SEVERITIES = frozenset({"CRITICAL", "HIGH"})
SECURITY_MD_PATH = Path("SECURITY.md")
SUPPLY_CHAIN_DOC_PATH = Path("docs/SUPPLY-CHAIN-SECURITY.md")
DEPENDABOT_CONFIG_PATH = Path(".github/dependabot.yml")


def test_openssf_scorecard_threshold() -> None:
    assert OPENSSF_SCORECARD_MIN >= 7.0


def test_pip_audit_blocks_critical_and_high() -> None:
    assert "CRITICAL" in PIP_AUDIT_FAIL_SEVERITIES
    assert "HIGH" in PIP_AUDIT_FAIL_SEVERITIES


def test_security_md_exists() -> None:
    assert SECURITY_MD_PATH.is_file()
    content = SECURITY_MD_PATH.read_text(encoding="utf-8")
    assert "vulnerability" in content.lower() or "security" in content.lower()


def test_supply_chain_doc_exists() -> None:
    assert SUPPLY_CHAIN_DOC_PATH.is_file()
    text = SUPPLY_CHAIN_DOC_PATH.read_text(encoding="utf-8")
    assert "OpenSSF" in text
    assert str(OPENSSF_SCORECARD_MIN) in text


def test_dependabot_config_exists() -> None:
    assert DEPENDABOT_CONFIG_PATH.is_file()
