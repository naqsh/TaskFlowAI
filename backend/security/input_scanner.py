from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.security.injection import InjectionMatch, PromptInjectionDetector


class ScanResult(BaseModel):
    """Result of an input security scan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    layer: Literal["regex"]
    is_violation: bool
    matched_pattern: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class SecurityViolationError(Exception):
    """Raised when input violates input security policy."""

    def __init__(self, scan: ScanResult) -> None:
        self.scan = scan
        super().__init__(
            f"security_violation_detected layer={scan.layer} pattern={scan.matched_pattern}"
        )


class InputSecurityScanner:
    """Input security scanner (Part 1: regex layer only).

    `LLAMAFIREWALL_ENABLED=false` would skip ML/constitutional layers in Part 2,
    but regex scanning is always applied to prevent known injection strings.
    """

    def __init__(self, detector: PromptInjectionDetector | None = None) -> None:
        self._detector = detector or PromptInjectionDetector()

        # Present for Part 2 compatibility. Regex is always active in Part 1.
        self._firewall_enabled = os.getenv("LLAMAFIREWALL_ENABLED", "true").lower() != "false"

    def scan(self, text: str) -> ScanResult:
        match: InjectionMatch | None = self._detector.detect(text)
        if match is None:
            return ScanResult(
                layer="regex", is_violation=False, matched_pattern=None, confidence=0.0
            )

        # Regex layer always classifies as a violation.
        return ScanResult(
            layer="regex",
            is_violation=True,
            matched_pattern=match.matched_pattern,
            confidence=match.confidence,
        )

    def scan_or_raise(self, text: str) -> None:
        result = self.scan(text)
        if result.is_violation:
            raise SecurityViolationError(result)
