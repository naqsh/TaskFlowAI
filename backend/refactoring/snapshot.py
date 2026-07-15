"""Snapshot and rollback for agentic refactoring (ADR-004)."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from backend.refactoring.sandbox import RefactoringSandbox, SandboxError


@dataclass
class CodeSnapshot:
    """In-memory/disk capture of file contents before patching."""

    snapshot_id: str
    files: dict[str, str] = field(default_factory=dict)
    staging_dir: Path | None = None


class SnapshotService:
    """Capture and restore sandbox files (Snapshot / Rollback stages)."""

    def __init__(self, sandbox: RefactoringSandbox) -> None:
        self._sandbox = sandbox

    def capture(self, relative_paths: list[str]) -> CodeSnapshot:
        snapshot_id = str(uuid.uuid4())
        staging = Path(tempfile.mkdtemp(prefix=f"tf-refactor-{snapshot_id}-"))
        files: dict[str, str] = {}
        for rel in relative_paths:
            path = self._sandbox.resolve(rel)
            if not path.is_file():
                msg = f"Cannot snapshot missing file: {rel}"
                raise SandboxError(msg)
            content = path.read_text(encoding="utf-8")
            files[rel] = content
            dest = staging / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        return CodeSnapshot(snapshot_id=snapshot_id, files=files, staging_dir=staging)

    def restore(self, snapshot: CodeSnapshot) -> list[str]:
        restored: list[str] = []
        for rel, content in snapshot.files.items():
            path = self._sandbox.resolve(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            restored.append(rel)
        return restored

    def cleanup(self, snapshot: CodeSnapshot) -> None:
        if snapshot.staging_dir is not None and snapshot.staging_dir.exists():
            shutil.rmtree(snapshot.staging_dir, ignore_errors=True)
