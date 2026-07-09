"""Tests for agent manifest signature verification (TF-060)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.kernel.config_loader import load_agent_manifest, verify_signature
from backend.kernel.errors import ConfigSignatureError


def test_valid_signature_loads_config() -> None:
    manifest = load_agent_manifest()
    assert "context_agent" in manifest.agents
    assert "tasks.list" in manifest.tool_allowlists["context_agent"]


def test_tampered_manifest_fails_verification(tmp_path: Path) -> None:
    manifest_path = tmp_path / "agent-manifest.json"
    sig_path = tmp_path / "agent-manifest.sig"
    key_dir = tmp_path / "keys"
    key_dir.mkdir()

    priv = Ed25519PrivateKey.generate()
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    (key_dir / "test.pub").write_bytes(pub_bytes)

    original = Path("infrastructure/agent-manifest.json").read_text(encoding="utf-8")
    manifest_path.write_text(original, encoding="utf-8")
    sig = priv.sign(manifest_path.read_bytes())
    sig_path.write_text(base64.b64encode(sig).decode())

    tampered = json.loads(original)
    tampered["version"] = "9.9.9"
    manifest_path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(ConfigSignatureError):
        verify_signature(manifest_path, sig_path, public_key_dir=key_dir)


def test_unsigned_manifest_fails_in_production_mode(tmp_path: Path) -> None:
    manifest_path = tmp_path / "agent-manifest.json"
    sig_path = tmp_path / "agent-manifest.sig"
    manifest_path.write_text('{"version":"1.0.0","agents":{},"tool_allowlists":{}}')

    with pytest.raises(ConfigSignatureError, match="signature required"):
        load_agent_manifest(manifest_path, require_signature=True, signature_path=sig_path)


def test_unsigned_manifest_allowed_when_not_required() -> None:
    manifest = load_agent_manifest(require_signature=False)
    assert manifest.version
