"""AI Bill of Materials loader and freshness validation (TF-055)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_BOM_PATH = Path("infrastructure/ai-bom.yaml")
BOM_STALE_DAYS = 7


@dataclass(frozen=True)
class AIBom:
    version: str
    last_updated: date
    owner: str
    models: tuple[dict[str, Any], ...]
    production_libraries: frozenset[str]
    runtime_model_ids: frozenset[str]


class BomValidationError(ValueError):
    """Raised when the AI-BOM fails validation."""


def _normalize_lib_name(name: str) -> str:
    return name.lower().replace("_", "-").split("[")[0]


def load_ai_bom(path: Path | str | None = None) -> AIBom:
    """Load and parse ``infrastructure/ai-bom.yaml``."""

    bom_path = Path(path) if path is not None else DEFAULT_BOM_PATH
    if not bom_path.is_file():
        msg = f"AI-BOM not found: {bom_path}"
        raise BomValidationError(msg)

    with bom_path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    last_updated_raw = raw.get("last_updated")
    if not isinstance(last_updated_raw, str):
        msg = "AI-BOM last_updated must be an ISO date string"
        raise BomValidationError(msg)

    try:
        last_updated = date.fromisoformat(last_updated_raw)
    except ValueError as exc:
        msg = f"invalid AI-BOM last_updated: {last_updated_raw}"
        raise BomValidationError(msg) from exc

    models_raw = raw.get("models", [])
    if not isinstance(models_raw, list):
        msg = "AI-BOM models must be a list"
        raise BomValidationError(msg)

    libs_raw = raw.get("production_libraries", [])
    if not isinstance(libs_raw, list):
        msg = "AI-BOM production_libraries must be a list"
        raise BomValidationError(msg)

    runtime_raw = raw.get("runtime_model_ids", [])
    if not isinstance(runtime_raw, list):
        msg = "AI-BOM runtime_model_ids must be a list"
        raise BomValidationError(msg)

    return AIBom(
        version=str(raw.get("version", "")),
        last_updated=last_updated,
        owner=str(raw.get("owner", "")),
        models=tuple(m for m in models_raw if isinstance(m, dict)),
        production_libraries=frozenset(str(x) for x in libs_raw),
        runtime_model_ids=frozenset(str(x) for x in runtime_raw),
    )


def validate_bom_freshness(
    bom: AIBom,
    *,
    now: date | None = None,
    stale_days: int = BOM_STALE_DAYS,
) -> str | None:
    """Return a warning message when BOM is older than ``stale_days``; else ``None``."""

    reference = now or datetime.now(UTC).date()
    age_days = (reference - bom.last_updated).days
    if age_days > stale_days:
        return f"AI-BOM stale: last_updated={bom.last_updated.isoformat()} ({age_days} days old)"
    return None


def validate_runtime_models(
    bom: AIBom,
    runtime_model_ids: set[str],
) -> list[str]:
    """Return model IDs present at runtime but missing from the BOM."""

    return sorted(runtime_model_ids - bom.runtime_model_ids)


def validate_production_libraries(
    bom: AIBom,
    pyproject_deps: set[str],
) -> list[str]:
    """Return production dependencies missing from the BOM library list."""

    bom_libs = {_normalize_lib_name(x) for x in bom.production_libraries}
    missing: list[str] = []
    for dep in sorted(pyproject_deps):
        normalized = _normalize_lib_name(dep)
        if normalized not in bom_libs:
            missing.append(dep)
    return missing
