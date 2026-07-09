from __future__ import annotations

import os
import re
from dataclasses import dataclass

from backend.logging_config import get_logger

logger = get_logger(__name__)

# Semantic heuristics used when LlamaFirewall model is unavailable (CI / no HF_TOKEN).
_SEMANTIC_JAILBREAK_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    (
        "semantic_override",
        re.compile(
            r"(?i)pretend\s+(you\s+)?(are|were)\s+(not\s+)?(bound|restricted|limited)",
            re.S,
        ),
        0.91,
    ),
    (
        "semantic_hypothetical",
        re.compile(r"(?i)hypothetically[,]?\s+(ignore|disregard|override)", re.S),
        0.9,
    ),
    (
        "semantic_developer_mode",
        re.compile(r"(?i)(developer|debug|maintenance)\s+mode\s+(enabled|on|activated)", re.S),
        0.92,
    ),
    (
        "semantic_instruction_injection",
        re.compile(r"(?i)new\s+instructions?\s*:\s*", re.S),
        0.89,
    ),
    (
        "semantic_roleplay_jailbreak",
        re.compile(r"(?i)act\s+as\s+(an?\s+)?(unrestricted|unfiltered)\s+ai", re.S),
        0.93,
    ),
]


@dataclass(frozen=True)
class PromptGuardResult:
    is_jailbreak: bool
    score: float
    label: str | None = None


class PromptGuardService:
    """PromptGuard 2 wrapper with heuristic fallback when model unavailable (TF-041)."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        block_threshold: float = 0.9,
        hf_token: str | None = None,
        app_env: str = "development",
    ) -> None:
        self._enabled = enabled
        self._block_threshold = block_threshold
        self._hf_token = hf_token or os.getenv("HF_TOKEN")
        self._app_env = app_env
        self._model_loaded = False
        self._model_failed = False

        if self._enabled and self._hf_token:
            self._try_load_model()

    def _try_load_model(self) -> None:
        try:
            # Optional heavy dependency — not required for CI.
            import importlib

            importlib.import_module("transformers")
            self._model_loaded = True
        except Exception:
            self._model_failed = True
            if self._app_env == "production":
                logger.error("prompt_guard_model_load_failed_fail_closed")
            else:
                logger.warning("prompt_guard_model_load_failed_using_heuristics")

    @property
    def available(self) -> bool:
        return self._enabled and (self._model_loaded or not self._model_failed)

    def score(self, text: str) -> PromptGuardResult:
        if not self._enabled:
            return PromptGuardResult(is_jailbreak=False, score=0.0)

        if not self._hf_token:
            logger.warning("prompt_guard_skipped_no_hf_token")
            return self._heuristic_score(text)

        if self._model_failed and self._app_env == "production":
            return PromptGuardResult(is_jailbreak=True, score=1.0, label="model_unavailable")

        if not self._model_loaded:
            return self._heuristic_score(text)

        # Real model inference deferred — heuristic path until transformers pipeline wired.
        return self._heuristic_score(text)

    def _heuristic_score(self, text: str) -> PromptGuardResult:
        best_score = 0.0
        best_label: str | None = None
        for label, pattern, confidence in _SEMANTIC_JAILBREAK_PATTERNS:
            if pattern.search(text):
                if confidence > best_score:
                    best_score = confidence
                    best_label = label

        is_jailbreak = best_score >= self._block_threshold
        return PromptGuardResult(is_jailbreak=is_jailbreak, score=best_score, label=best_label)
