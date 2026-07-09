#!/usr/bin/env python3
"""CI gate: audit production deps and fail on CRITICAL/HIGH CVEs (TF-056)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Documented no-fix transitive dependency — see docs/adr/ADR-003-ecdsa-pip-audit-exception.md
IGNORED_VULN_IDS = frozenset(
    {
        "PYSEC-2026-1325",
        "GHSA-wj6h-64fc-37mp",
        "CVE-2024-23342",
    }
)

FAIL_SEVERITIES = frozenset({"CRITICAL", "HIGH"})


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _export_production_requirements(root: Path, output: Path) -> None:
    subprocess.run(
        [
            "uv",
            "export",
            "--no-dev",
            "--no-hashes",
            "--format",
            "requirements-txt",
            "-o",
            str(output),
        ],
        cwd=root,
        check=True,
    )


def _run_pip_audit(root: Path, requirements: Path) -> dict[str, object]:
    ignore_args: list[str] = []
    for vuln_id in sorted(IGNORED_VULN_IDS):
        ignore_args.extend(["--ignore-vuln", vuln_id])

    proc = subprocess.run(
        [
            "uv",
            "run",
            "pip-audit",
            "-r",
            str(requirements),
            "-f",
            "json",
            "--desc",
            "off",
            *ignore_args,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if not proc.stdout.strip():
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode or 1)
    return json.loads(proc.stdout)


def _collect_vulnerabilities(report: dict[str, object]) -> list[tuple[str, str, str]]:
    findings: list[tuple[str, str, str]] = []
    for dep in report.get("dependencies", []):
        if not isinstance(dep, dict):
            continue
        name = str(dep.get("name", "unknown"))
        vulns = dep.get("vulns", [])
        if not isinstance(vulns, list):
            continue
        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue
            vuln_id = str(vuln.get("id", "unknown"))
            severity = _severity_from_vuln(vuln)
            findings.append((name, vuln_id, severity))
    return findings


def _severity_from_vuln(vuln: dict[str, object]) -> str:
    """Map pip-audit/OSV payload to a coarse severity band."""
    for alias in vuln.get("aliases", []):
        if isinstance(alias, str) and alias.startswith("CVE-"):
            # pip-audit JSON does not include CVSS; treat unknown as HIGH (fail-safe).
            return "HIGH"
    return "HIGH"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production pip-audit CI gate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print policy constants and exit 0",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"fail_severities={sorted(FAIL_SEVERITIES)}")
        print(f"ignored_vulns={sorted(IGNORED_VULN_IDS)}")
        return 0

    root = _root()
    req_path = root / ".pip-audit-prod-reqs.txt"
    try:
        _export_production_requirements(root, req_path)
        report = _run_pip_audit(root, req_path)
    finally:
        req_path.unlink(missing_ok=True)

    blocking = [
        (name, vuln_id, severity)
        for name, vuln_id, severity in _collect_vulnerabilities(report)
        if severity in FAIL_SEVERITIES
    ]
    if blocking:
        for name, vuln_id, severity in blocking:
            print(f"BLOCK {severity}: {name} ({vuln_id})", file=sys.stderr)
        return 1

    print("pip-audit gate passed (no blocking CRITICAL/HIGH CVEs in production deps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
