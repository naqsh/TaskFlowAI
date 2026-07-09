"""Agent configuration manifest loader with signature verification (TF-060)."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.kernel.errors import ConfigSignatureError

DEFAULT_MANIFEST_PATH = Path("infrastructure/agent-manifest.json")
DEFAULT_SIGNATURE_PATH = Path("infrastructure/agent-manifest.sig")
DEFAULT_PUBLIC_KEY_DIR = Path("infrastructure/keys")


@dataclass(frozen=True)
class AgentManifest:
    version: str
    agents: dict[str, dict[str, Any]]
    tool_allowlists: dict[str, list[str]]


def _load_public_keys(key_dir: Path) -> list[bytes]:
    keys: list[bytes] = []
    if not key_dir.is_dir():
        return keys
    for path in sorted(key_dir.glob("*.pub")):
        keys.append(path.read_bytes())
    return keys


def verify_signature(
    manifest_path: Path,
    signature_path: Path,
    *,
    public_key_dir: Path = DEFAULT_PUBLIC_KEY_DIR,
) -> None:
    """Verify ed25519 signature over manifest bytes (supports key rotation)."""

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    manifest_bytes = manifest_path.read_bytes()
    signature_b64 = signature_path.read_text(encoding="utf-8").strip()
    signature = base64.b64decode(signature_b64)

    public_keys = _load_public_keys(public_key_dir)
    if not public_keys:
        msg = f"no public keys found in {public_key_dir}"
        raise ConfigSignatureError(msg)

    last_error: Exception | None = None
    for key_data in public_keys:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(key_data)
            public_key.verify(signature, manifest_bytes)
            return
        except (InvalidSignature, ValueError) as exc:
            last_error = exc
            continue

    msg = "agent manifest signature verification failed"
    raise ConfigSignatureError(msg) from last_error


def load_agent_manifest(
    manifest_path: Path | None = None,
    *,
    require_signature: bool = False,
    signature_path: Path | None = None,
) -> AgentManifest:
    """Load manifest; verify signature when required or when signature file exists."""

    path = manifest_path or DEFAULT_MANIFEST_PATH
    if not path.is_file():
        msg = f"agent manifest not found: {path}"
        raise ConfigSignatureError(msg)

    sig_path = signature_path or DEFAULT_SIGNATURE_PATH
    if require_signature or sig_path.is_file():
        if not sig_path.is_file():
            msg = f"signature required but missing: {sig_path}"
            raise ConfigSignatureError(msg)
        verify_signature(path, sig_path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    agents_raw = raw.get("agents", {})
    allowlists_raw = raw.get("tool_allowlists", {})
    if not isinstance(agents_raw, dict) or not isinstance(allowlists_raw, dict):
        msg = "invalid agent manifest structure"
        raise ConfigSignatureError(msg)

    agents = {str(k): v for k, v in agents_raw.items() if isinstance(v, dict)}
    tool_allowlists = {
        str(k): [str(x) for x in v] for k, v in allowlists_raw.items() if isinstance(v, list)
    }
    return AgentManifest(
        version=str(raw.get("version", "")),
        agents=agents,
        tool_allowlists=tool_allowlists,
    )
