from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.logging_config import get_logger
from backend.metrics import SECURITY_VIOLATION_DETECTED_TOTAL
from backend.security.constitutional import ConstitutionalClassifier, ConstitutionalMatch
from backend.security.injection import InjectionMatch, PromptInjectionDetector
from backend.security.prompt_guard import PromptGuardResult, PromptGuardService
from backend.security.session_violations import SessionViolationLimiter

logger = get_logger(__name__)

ScanLayer = Literal["regex", "ml", "constitutional", "rate_limit"]


class ScanResult(BaseModel):
    """Result of an input security scan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    layer: ScanLayer
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
    """Three-layer input security scanner: regex → ML → constitutional (TF-041)."""

    def __init__(
        self,
        detector: PromptInjectionDetector | None = None,
        prompt_guard: PromptGuardService | None = None,
        constitutional: ConstitutionalClassifier | None = None,
        *,
        llamafirewall_enabled: bool = True,
        block_threshold: float = 0.9,
        hf_token: str | None = None,
        app_env: str = "development",
        layer_timeout_seconds: float = 5.0,
        violation_limiter: SessionViolationLimiter | None = None,
    ) -> None:
        self._detector = detector or PromptInjectionDetector()
        self._prompt_guard = prompt_guard or PromptGuardService(
            enabled=llamafirewall_enabled,
            block_threshold=block_threshold,
            hf_token=hf_token,
            app_env=app_env,
        )
        self._constitutional = constitutional or ConstitutionalClassifier(app_env=app_env)
        self._layer_timeout = layer_timeout_seconds
        self._violation_limiter = violation_limiter or SessionViolationLimiter()

    def scan(self, text: str, *, session_key: str | None = None) -> ScanResult:
        if session_key and self._violation_limiter.is_blocked(session_key):
            return ScanResult(
                layer="rate_limit",
                is_violation=True,
                matched_pattern="session_violation_rate_limit",
                confidence=1.0,
            )

        regex_result = self._run_layer("regex", lambda: self._scan_regex(text))
        if regex_result.is_violation:
            self._record_violation(regex_result, session_key=session_key)
            return regex_result

        ml_result = self._run_layer("ml", lambda: self._scan_ml(text))
        if ml_result.is_violation:
            self._record_violation(ml_result, session_key=session_key)
            return ml_result

        constitutional_result = self._run_layer(
            "constitutional", lambda: self._scan_constitutional(text)
        )
        if constitutional_result.is_violation:
            self._record_violation(constitutional_result, session_key=session_key)
            return constitutional_result

        return ScanResult(
            layer="constitutional",
            is_violation=False,
            matched_pattern=None,
            confidence=0.0,
        )

    def scan_or_raise(self, text: str, *, session_key: str | None = None) -> None:
        result = self.scan(text, session_key=session_key)
        if result.is_violation:
            raise SecurityViolationError(result)

    def _run_layer(self, layer: ScanLayer, fn: object) -> ScanResult:
        start = time.perf_counter()
        try:
            result: ScanResult = fn()  # type: ignore[operator]
        except Exception:
            logger.exception("input_scanner_layer_failed", layer=layer)
            return ScanResult(
                layer=layer,
                is_violation=True,
                matched_pattern="layer_failure",
                confidence=1.0,
            )
        elapsed = time.perf_counter() - start
        if elapsed > self._layer_timeout:
            logger.warning("input_scanner_layer_timeout", layer=layer, elapsed=elapsed)
            return ScanResult(
                layer=layer,
                is_violation=True,
                matched_pattern="layer_timeout",
                confidence=1.0,
            )
        return result

    def _scan_regex(self, text: str) -> ScanResult:
        match: InjectionMatch | None = self._detector.detect(text)
        if match is None:
            return ScanResult(
                layer="regex", is_violation=False, matched_pattern=None, confidence=0.0
            )
        return ScanResult(
            layer="regex",
            is_violation=True,
            matched_pattern=match.matched_pattern,
            confidence=match.confidence,
        )

    def _scan_ml(self, text: str) -> ScanResult:
        pg_result: PromptGuardResult = self._prompt_guard.score(text)
        if not pg_result.is_jailbreak:
            return ScanResult(
                layer="ml", is_violation=False, matched_pattern=None, confidence=pg_result.score
            )
        return ScanResult(
            layer="ml",
            is_violation=True,
            matched_pattern=pg_result.label,
            confidence=pg_result.score,
        )

    def _scan_constitutional(self, text: str) -> ScanResult:
        match: ConstitutionalMatch | None = self._constitutional.classify(text)
        if match is None:
            return ScanResult(
                layer="constitutional",
                is_violation=False,
                matched_pattern=None,
                confidence=0.0,
            )
        return ScanResult(
            layer="constitutional",
            is_violation=True,
            matched_pattern=match.rule_id,
            confidence=match.confidence,
        )

    def _record_violation(self, result: ScanResult, *, session_key: str | None) -> None:
        if session_key:
            self._violation_limiter.record_violation(session_key)
        SECURITY_VIOLATION_DETECTED_TOTAL.labels(layer=result.layer).inc()
        logger.warning(
            "security_violation_detected",
            layer=result.layer,
            pattern=result.matched_pattern,
            confidence=result.confidence,
            session_key=session_key,
        )
