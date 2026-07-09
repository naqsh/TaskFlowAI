#!/usr/bin/env python3
"""CLI: validate AI-BOM against runtime models and pyproject production deps (TF-055)."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from backend.security.bom import (
    DEFAULT_BOM_PATH,
    load_ai_bom,
    validate_bom_freshness,
    validate_production_libraries,
    validate_runtime_models,
)

# Runtime models configured in settings / proposal (not all may be active per env).
EXPECTED_RUNTIME_MODELS = {
    "gpt-5.5",
    "claude-opus-4-8",
    "gpt-4o-mini",
    "llama-3.1",
    "prompt-guard-2",
}


def _load_pyproject_production_deps(root: Path) -> set[str]:
    pyproject = root / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    return {str(d).split(">=")[0].split("==")[0].strip() for d in deps}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate TaskFlow AI-BOM")
    parser.add_argument(
        "--bom-path",
        type=Path,
        default=DEFAULT_BOM_PATH,
        help="Path to ai-bom.yaml",
    )
    parser.add_argument(
        "--warn-stale",
        action="store_true",
        help="Exit 2 when BOM is older than 7 days (CI weekly check)",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    bom = load_ai_bom(args.bom_path)

    stale_warning = validate_bom_freshness(bom)
    if stale_warning:
        print(f"WARNING: {stale_warning}", file=sys.stderr)
        if args.warn_stale:
            return 2

    missing_models = validate_runtime_models(bom, EXPECTED_RUNTIME_MODELS)
    if missing_models:
        print(f"ERROR: runtime models missing from BOM: {', '.join(missing_models)}", file=sys.stderr)
        return 1

    pyproject_deps = _load_pyproject_production_deps(root)
    missing_libs = validate_production_libraries(bom, pyproject_deps)
    if missing_libs:
        print(
            f"ERROR: pyproject production deps missing from BOM: {', '.join(missing_libs)}",
            file=sys.stderr,
        )
        return 1

    print(f"AI-BOM valid: version={bom.version} last_updated={bom.last_updated.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
