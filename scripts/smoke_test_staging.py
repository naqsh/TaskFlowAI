#!/usr/bin/env python3
"""Staging smoke tests for deployment gates (TF-059)."""

from __future__ import annotations

import argparse
import sys
import time

import httpx

DEFAULT_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def _check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")
    return ok


def run_smoke(base_url: str, *, retries: int = DEFAULT_RETRIES) -> int:
    base = base_url.rstrip("/")
    last_error = ""

    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(timeout=30.0) as client:
                health = client.get(f"{base}/health")
                if not _check("/health", health.status_code == 200, str(health.status_code)):
                    raise RuntimeError("health failed")

                metrics = client.get(f"{base}/metrics")
                if not _check("/metrics", metrics.status_code == 200):
                    raise RuntimeError("metrics failed")

                ping = client.get(f"{base}/api/v1/ping")
                if not _check("/api/v1/ping", ping.status_code == 200):
                    raise RuntimeError("ping failed")

            print("Smoke tests passed")
            return 0
        except Exception as exc:
            last_error = str(exc)
            if attempt < retries:
                print(f"Retry {attempt}/{retries} after error: {last_error}")
                time.sleep(RETRY_DELAY_SECONDS)

    print(f"Smoke tests failed after {retries} attempts: {last_error}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TaskFlow staging smoke tests")
    parser.add_argument("base_url", help="Staging base URL, e.g. https://staging-api.example.com")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    args = parser.parse_args(argv)
    return run_smoke(args.base_url, retries=args.retries)


if __name__ == "__main__":
    raise SystemExit(main())
