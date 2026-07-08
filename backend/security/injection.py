from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionMatch:
    matched_pattern: str
    confidence: float


class PromptInjectionDetector:
    """Regex-based prompt injection detector (MVP Part 1).

    Notes:
    - Only the regex layer is implemented in Part 1.
    - ML/constitutional layers are intentionally left as stubs.
    """

    def __init__(self) -> None:
        # Keep patterns explicit and anchored to common jailbreak substrings.
        # `re.S` allows whitespace/newlines between tokens to still match.
        self._patterns: list[tuple[str, re.Pattern[str]]] = [
            (
                "ignore_previous",
                re.compile(r"ignore\s+previous\s+(instructions?|instruction)", re.I | re.S),
            ),
            ("disregard_training", re.compile(r"disregard\s+training", re.I | re.S)),
            ("dan_mode", re.compile(r"\bdan\b\s*mode", re.I | re.S)),
            ("system_tag_brackets", re.compile(r"\[\[system\]\]", re.I | re.S)),
            ("im_start_token", re.compile(r"<\|\s*im_start\s*\|>", re.I | re.S)),
            ("codeblock_system", re.compile(r"```+\s*system", re.I | re.S)),
        ]

    @staticmethod
    def _normalize(text: str) -> str:
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def _try_decode_base64(text: str) -> str | None:
        # Heuristic: base64 alphabet + padding; avoid decoding arbitrary user text.
        if not re.fullmatch(r"[A-Za-z0-9+/=\s]+", text.strip()):
            return None
        if len(text) < 20:
            return None

        try:
            raw = base64.b64decode(text, validate=False)
        except binascii.Error:
            return None
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return None

    @staticmethod
    def _try_decode_hex(text: str) -> str | None:
        stripped = text.strip().replace(" ", "")
        if not stripped:
            return None
        if len(stripped) < 20 or len(stripped) % 2 != 0:
            return None
        if not re.fullmatch(r"[0-9a-fA-F]+", stripped):
            return None

        try:
            raw = bytes.fromhex(stripped)
        except ValueError:
            return None
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return None

    def detect(self, text: str) -> InjectionMatch | None:
        """Return the first detected injection match, if any."""

        normalized = self._normalize(text)

        # Try decoding common obfuscation patterns before matching regexes.
        candidates: list[str] = [normalized]
        decoded_b64 = self._try_decode_base64(normalized)
        if decoded_b64:
            candidates.append(decoded_b64)
        decoded_hex = self._try_decode_hex(normalized)
        if decoded_hex:
            candidates.append(decoded_hex)

        for candidate in candidates:
            for label, pattern in self._patterns:
                if pattern.search(candidate):
                    # Regex layer is best-effort; keep confidence high for crisp matches.
                    return InjectionMatch(matched_pattern=label, confidence=0.9)

        return None
