"""Verify and optional command gate after patching (ADR-004)."""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path

from backend.refactoring.sandbox import RefactoringSandbox


@dataclass(frozen=True, slots=True)
class VerifyResult:
    passed: bool
    outcome: str  # pass | fail | skipped
    details: str


class VerifyService:
    """Re-parse changed files and optionally run a sandbox-rooted verify command."""

    def __init__(
        self,
        sandbox: RefactoringSandbox,
        *,
        verify_command: str = "",
        timeout_seconds: int = 60,
    ) -> None:
        self._sandbox = sandbox
        self._verify_command = verify_command.strip()
        self._timeout = timeout_seconds

    def verify_files(self, relative_paths: list[str]) -> VerifyResult:
        parse_errors: list[str] = []
        for rel in relative_paths:
            path = self._sandbox.resolve(rel)
            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=str(path))
            except (OSError, SyntaxError) as exc:
                parse_errors.append(f"{rel}: {exc}")

        if parse_errors:
            return VerifyResult(
                passed=False,
                outcome="fail",
                details="; ".join(parse_errors),
            )

        if not self._verify_command:
            return VerifyResult(
                passed=True,
                outcome="pass",
                details="ast.parse ok; no external verify command configured",
            )

        return self._run_command(self._sandbox.root)

    def _run_command(self, cwd: Path) -> VerifyResult:
        try:
            completed = subprocess.run(  # noqa: S603 — command from trusted settings
                self._verify_command,
                shell=True,  # noqa: S602 — admin-configured verify gate only
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(
                passed=False,
                outcome="fail",
                details=f"verify command timed out after {self._timeout}s",
            )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "non-zero exit").strip()
            return VerifyResult(passed=False, outcome="fail", details=detail[:2000])
        return VerifyResult(
            passed=True,
            outcome="pass",
            details=(completed.stdout or "ok").strip()[:2000],
        )
