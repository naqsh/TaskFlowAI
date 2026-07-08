from __future__ import annotations

from pathlib import Path

import yaml

_CORPUS_DIR = Path(__file__).resolve().parent
_JAILBREAK = _CORPUS_DIR / "jailbreak_corpus.yaml"
_LEGITIMATE = _CORPUS_DIR / "legitimate_tasks_corpus.yaml"


def _load_payloads(path: Path) -> list[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(raw.get("payloads", []))


def test_jailbreak_corpus_inventory_sync() -> None:
    """Corpus file counts must match loaded payloads (AGENT.md sync gate)."""
    jailbreak = _load_payloads(_JAILBREAK)
    legitimate = _load_payloads(_LEGITIMATE)
    assert len(jailbreak) == 40
    assert len(legitimate) == 10
