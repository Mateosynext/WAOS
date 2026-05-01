#!/usr/bin/env python3
"""Additional release hardening checks for WAOS source artifacts.

The checker intentionally validates source-controlled release files, not
platform-generated runtime environments. Render may create or restore .venv
before the release gate runs, so Git checkouts are scanned through git ls-files.
Extracted release ZIPs still fall back to a filesystem walk.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_FILE_BYTES = int(os.environ.get("WAOS_HARDEN_MAX_FILE_BYTES", "50000000"))
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo", ".log", ".pem", ".key", ".p12", ".pfx"}
FORBIDDEN_SOURCE_DIRS = {
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "test-results",
    "playwright-report",
    ".turbo",
}
NON_SOURCE_RUNTIME_DIRS = {".git", ".venv", "venv", "env", ".tox", ".nox"}
FORBIDDEN_TRACKED_DIRS = FORBIDDEN_SOURCE_DIRS | (NON_SOURCE_RUNTIME_DIRS - {".git"})
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


def _git_tracked_files() -> list[Path]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0 or not completed.stdout:
        return []
    files: list[Path] = []
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            relative = raw.decode("utf-8")
        except UnicodeDecodeError:
            relative = raw.decode("utf-8", errors="replace")
        files.append(ROOT / relative)
    return sorted(files)


def _check_file(path: Path, relative: str, errors: list[str]) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        errors.append(f"cannot stat {relative}: {exc}")
        return
    if stat.S_ISLNK(mode):
        errors.append(f"symlink file is not allowed: {relative}")
        return
    if not stat.S_ISREG(mode):
        errors.append(f"special file is not allowed: {relative}")
        return
    if path.suffix in FORBIDDEN_SUFFIXES:
        errors.append(f"forbidden generated/secret-like file suffix: {relative}")
    try:
        size = path.stat().st_size
    except OSError as exc:
        errors.append(f"cannot stat {relative}: {exc}")
        return
    if size > MAX_FILE_BYTES:
        errors.append(f"unexpectedly large release source file: {relative} ({size} bytes)")


def _scan_git_tracked(errors: list[str]) -> bool:
    tracked = _git_tracked_files()
    if not tracked:
        return False
    for path in tracked:
        relative = rel(path)
        parts = set(Path(relative).parts[:-1])
        forbidden_parts = sorted(parts & FORBIDDEN_TRACKED_DIRS)
        for part in forbidden_parts:
            errors.append(f"tracked generated/runtime directory is not allowed: {relative} (under {part})")
        _check_file(path, relative, errors)
    return True


def _scan_filesystem(errors: list[str]) -> None:
    for current, dirs, files in os.walk(ROOT):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in sorted(dirs):
            path = current_path / name
            relative = rel(path)
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                errors.append(f"cannot stat {relative}: {exc}")
                continue
            if stat.S_ISLNK(mode):
                errors.append(f"symlink directory is not allowed: {relative}")
                continue
            if name in NON_SOURCE_RUNTIME_DIRS:
                continue
            if name in FORBIDDEN_SOURCE_DIRS:
                errors.append(f"generated/cache directory is not allowed: {relative}")
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in sorted(files):
            path = current_path / name
            _check_file(path, rel(path), errors)


def main() -> int:
    errors: list[str] = []
    scan_mode = "git-tracked" if _scan_git_tracked(errors) else "filesystem"
    if scan_mode == "filesystem":
        _scan_filesystem(errors)

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
        print(f"[source-hardening:scan] mode={scan_mode}")
        for error in errors[:100]:
            print("-", error)
        if len(errors) > 100:
            print(f"- ... {len(errors) - 100} more")
        return 1
    print(f"[source-hardening:ok] source tree, CI gates and deterministic release gate are hardened; scan={scan_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
