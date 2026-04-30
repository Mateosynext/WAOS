#!/usr/bin/env python3
"""Additional release hardening checks for WAOS source artifacts."""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_FILE_BYTES = int(os.environ.get("WAOS_HARDEN_MAX_FILE_BYTES", "50000000"))
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo", ".log", ".pem", ".key", ".p12", ".pfx"}
FORBIDDEN_DIRS = {"node_modules", ".next", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", "test-results", "playwright-report", ".turbo"}
REQUIRED_CI_NEEDLES = [
    "set -Eeuo pipefail",
    "timeout",
    "npm ci",
    "npm audit --audit-level",
    "npm run typecheck",
    "npm run build",
    "npm run test:node",
    "pip_audit",
    "pytest -q backend/tests",
    "WAOS_REQUIRE_LIVE_AI_EVALS",
]
REQUIRED_RELEASE_GATE_NEEDLES = [
    "timeout=int(os.environ.get('WAOS_GATE_STEP_TIMEOUT'",
    "run_frontend_guardrails()",
    "run_artifact_integrity()",
    "run_ai_evals()",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    errors: list[str] = []
    for current, dirs, files in os.walk(ROOT):
        current_path = Path(current)
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in list(dirs):
            path = current_path / name
            relative = rel(path)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                errors.append(f"symlink directory is not allowed: {relative}")
            if name in FORBIDDEN_DIRS:
                errors.append(f"generated/cache directory is not allowed: {relative}")
        for name in sorted(files):
            path = current_path / name
            relative = rel(path)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                errors.append(f"symlink file is not allowed: {relative}")
                continue
            if not stat.S_ISREG(mode):
                errors.append(f"special file is not allowed: {relative}")
                continue
            if path.suffix in FORBIDDEN_SUFFIXES:
                errors.append(f"forbidden generated/secret-like file suffix: {relative}")
            try:
                size = path.stat().st_size
            except OSError as exc:
                errors.append(f"cannot stat {relative}: {exc}")
                continue
            if size > MAX_FILE_BYTES:
                errors.append(f"unexpectedly large release source file: {relative} ({size} bytes)")
    ci = ROOT / "scripts" / "validate_release_in_ci.sh"
    gate = ROOT / "backend" / "scripts" / "release_gate.py"
    if ci.exists():
        text = ci.read_text(encoding="utf-8", errors="ignore")
        for needle in REQUIRED_CI_NEEDLES:
            if needle not in text:
                errors.append(f"validate_release_in_ci.sh missing hardening needle: {needle}")
    else:
        errors.append("missing scripts/validate_release_in_ci.sh")
    if gate.exists():
        text = gate.read_text(encoding="utf-8", errors="ignore")
        for needle in REQUIRED_RELEASE_GATE_NEEDLES:
            if needle not in text:
                errors.append(f"release_gate.py missing hardening needle: {needle}")
    else:
        errors.append("missing backend/scripts/release_gate.py")
    if errors:
        print("[source-hardening:fail] release source hardening failed")
        for error in errors[:100]:
            print("-", error)
        if len(errors) > 100:
            print(f"- ... {len(errors) - 100} more")
        return 1
    print("[source-hardening:ok] source tree, CI gates and deterministic release gate are hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
