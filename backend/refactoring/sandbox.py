"""Sandbox path jail for agentic refactoring (ADR-004)."""

from __future__ import annotations

from pathlib import Path


class SandboxError(ValueError):
    """Raised when a path escapes the configured sandbox root."""


class RefactoringSandbox:
    """Resolve and validate paths under an allowlisted root."""

    def __init__(self, root: str | Path) -> None:
        resolved = Path(root).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            msg = f"Refactoring sandbox root does not exist or is not a directory: {resolved}"
            raise SandboxError(msg)
        self.root = resolved

    def resolve(self, relative_or_abs: str | Path) -> Path:
        """Resolve a path and assert it stays inside the sandbox."""
        candidate = Path(relative_or_abs)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            msg = f"Path escapes refactoring sandbox: {resolved}"
            raise SandboxError(msg) from exc
        return resolved

    def relative_to_root(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root)).replace("\\", "/")

    def iter_python_files(self) -> list[Path]:
        return sorted(p for p in self.root.rglob("*.py") if p.is_file())
