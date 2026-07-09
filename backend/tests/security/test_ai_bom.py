"""Tests for AI Bill of Materials validation (TF-055)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from backend.security.bom import (
    BomValidationError,
    load_ai_bom,
    validate_bom_freshness,
    validate_production_libraries,
    validate_runtime_models,
)


def test_load_ai_bom_success() -> None:
    bom = load_ai_bom()
    assert bom.version == "1.0.0"
    assert bom.runtime_model_ids >= {"gpt-5.5", "prompt-guard-2"}
    assert "fastapi" in bom.production_libraries


def test_validate_runtime_models_missing() -> None:
    bom = load_ai_bom()
    missing = validate_runtime_models(bom, {"gpt-5.5", "unknown-model"})
    assert missing == ["unknown-model"]


def test_validate_bom_freshness_stale() -> None:
    bom = load_ai_bom()
    stale = validate_bom_freshness(bom, now=date(2026, 7, 20))
    assert stale is not None
    assert "stale" in stale.lower()


def test_validate_bom_freshness_fresh() -> None:
    bom = load_ai_bom()
    assert validate_bom_freshness(bom, now=date(2026, 7, 9)) is None


def test_validate_production_libraries_missing(tmp_path: Path) -> None:
    bom = load_ai_bom()
    missing = validate_production_libraries(bom, {"fastapi", "not-in-bom"})
    assert "not-in-bom" in missing


def test_load_ai_bom_missing_file(tmp_path: Path) -> None:
    with pytest.raises(BomValidationError, match="not found"):
        load_ai_bom(tmp_path / "missing.yaml")
