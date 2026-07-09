#!/usr/bin/env python3
"""Sign agent-manifest.json with ed25519 private key (TF-060 CI step)."""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEFAULT_MANIFEST = Path("infrastructure/agent-manifest.json")
DEFAULT_SIG = Path("infrastructure/agent-manifest.sig")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sign agent manifest")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_SIG)
    parser.add_argument(
        "--private-key-pem",
        type=str,
        default=os.environ.get("AGENT_MANIFEST_PRIVATE_KEY", ""),
        help="PEM private key or AGENT_MANIFEST_PRIVATE_KEY env",
    )
    parser.add_argument(
        "--private-key-file",
        type=Path,
        default=None,
        help="Dev-only PEM file (default: infrastructure/keys/agent-manifest-dev.pem)",
    )
    args = parser.parse_args(argv)

    pem_bytes: bytes
    if args.private_key_pem:
        pem_bytes = args.private_key_pem.encode()
    else:
        key_file = args.private_key_file or Path("infrastructure/keys/agent-manifest-dev.pem")
        if not key_file.is_file():
            print("ERROR: private key not provided", file=sys.stderr)
            return 1
        pem_bytes = key_file.read_bytes()

    private_key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        print("ERROR: key must be ed25519", file=sys.stderr)
        return 1

    manifest_bytes = args.manifest.read_bytes()
    signature = private_key.sign(manifest_bytes)
    args.output.write_text(base64.b64encode(signature).decode())
    print(f"signed {args.manifest} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
