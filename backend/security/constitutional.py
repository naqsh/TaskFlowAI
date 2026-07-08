from __future__ import annotations

import re
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from backend.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"
_RULE_TIMEOUT_SECONDS = 0.1


@dataclass(frozen=True)
class ConstitutionalMatch:
    rule_id: str
    confidence: float


class _RuleTimeout(Exception):
    pass


def _alarm_handler(_signum: int, _frame: object) -> None:
    raise _RuleTimeout


class ConstitutionalClassifier:
    """Layer 3 constitutional policy classifier (TF-047)."""

    def __init__(
        self,
        *,
        rules_path: Path | None = None,
        app_env: str = "development",
    ) -> None:
        self._rules_path = rules_path or _DEFAULT_RULES_PATH
        self._app_env = app_env
        self._rules: list[tuple[str, re.Pattern[str], float]] = []
        self._version = "0.0.0"
        self._load_rules()

    @property
    def version(self) -> str:
        return self._version

    def _load_rules(self) -> None:
        if not self._rules_path.exists():
            if self._app_env == "production":
                msg = f"constitutional rules missing: {self._rules_path}"
                raise FileNotFoundError(msg)
            logger.warning("constitutional_rules_missing", path=str(self._rules_path))
            return

        raw: dict[str, Any] = yaml.safe_load(self._rules_path.read_text(encoding="utf-8"))
        self._version = str(raw.get("version", "0.0.0"))
        compiled: list[tuple[str, re.Pattern[str], float]] = []
        for rule in raw.get("rules", []):
            rule_id = str(rule["id"])
            pattern = re.compile(str(rule["pattern"]), re.I | re.S)
            confidence = float(rule.get("confidence", 0.85))
            compiled.append((rule_id, pattern, confidence))
        self._rules = compiled

    def classify(self, text: str) -> ConstitutionalMatch | None:
        for rule_id, pattern, confidence in self._rules:
            if self._match_with_timeout(pattern, text):
                return ConstitutionalMatch(rule_id=rule_id, confidence=confidence)
        return None

    @staticmethod
    def _match_with_timeout(pattern: re.Pattern[str], text: str) -> bool:
        if not hasattr(signal, "SIGALRM"):
            return pattern.search(text) is not None

        previous = signal.signal(signal.SIGALRM, _alarm_handler)
        if hasattr(signal, "setitimer"):
            signal.setitimer(signal.ITIMER_REAL, _RULE_TIMEOUT_SECONDS)  # type: ignore[attr-defined]
        elif hasattr(signal, "alarm"):
            signal.alarm(1)  # type: ignore[attr-defined]
        try:
            return pattern.search(text) is not None
        except _RuleTimeout:
            logger.warning("constitutional_rule_timeout", pattern=pattern.pattern)
            return False
        finally:
            if hasattr(signal, "setitimer"):
                signal.setitimer(signal.ITIMER_REAL, 0)  # type: ignore[attr-defined]
            elif hasattr(signal, "alarm"):
                signal.alarm(0)  # type: ignore[attr-defined]
            signal.signal(signal.SIGALRM, previous)
