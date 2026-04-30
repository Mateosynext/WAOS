#!/usr/bin/env python3
"""Fail-fast integrity guard for source release artifacts.

This script is intentionally dependency-free so it can run before npm/pip installs.
It checks that the shipped source tree is clean, reproducible, and free of common
build outputs or accidental local secrets.
"""
from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "backend/scripts/validate_release_candidate.py",
    "backend/scripts/check_repo_hygiene.py",
    "backend/scripts/release_gate.py",
    "backend/scripts/check_release_artifact_integrity.py",
    "scripts/validate_release_in_ci.sh",
    "scripts/validate_zip_reproducible.sh",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/scripts/check-local-imports.mjs",
    ".github/workflows/waos-release-validation.yml",
]

EXECUTABLE_FILES = [
    "scripts/validate_release_in_ci.sh",
    "scripts/validate_zip_reproducible.sh",
    "backend/scripts/run_ci_checks.sh",
]

FORBIDDEN_NAMES = {
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

FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tsbuildinfo",
    ".log",
}

FORBIDDEN_EXACT_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "backend/.env",
    "frontend/.env",
    "frontend/.env.local",
    "frontend/.env.production",
}

SECRET_SCAN_EXTS = {
    ".env",
    ".json",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".py",
    ".sh",
    ".yaml",
    ".yml",
    ".md",
    ".toml",
    ".ini",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{32,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?(?!changeme|change-me|placeholder|example|dummy|test|your_|<|\$\{)[A-Za-z0-9_./+=:-]{20,}"),
]

ALLOWLIST_SECRET_FILES = {
    "backend/.env.example",
    "backend/.env.render.example",
    "frontend/.env.production.example",
    "docs/AI_EVALS_PRODUCTION_READINESS_P1_3_2026-04-29.md",
    "docs/FRONTEND_CERTIFICATION_REQUIREMENT_P1_7_2026-04-30.md",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_executable(path: Path) -> bool:
    mode = path.stat().st_mode
    return bool(mode & stat.S_IXUSR)


def iter_paths() -> list[Path]:
    paths: list[Path] = []
    for current, dirs, files in os.walk(ROOT):
        current_path = Path(current)
        dirs[:] = sorted(dirs)
        files = sorted(files)
        for name in dirs:
            paths.append(current_path / name)
        for name in files:
            paths.append(current_path / name)
    return paths


def check_required(errors: list[str]) -> None:
    for item in REQUIRED_FILES:
        if not (ROOT / item).is_file():
            errors.append(f"missing required file: {item}")
    for item in EXECUTABLE_FILES:
        path = ROOT / item
        if not path.is_file():
            errors.append(f"missing executable file: {item}")
        elif not is_executable(path):
            errors.append(f"file is not executable: {item}")


def check_forbidden_artifacts(errors: list[str]) -> None:
    for path in iter_paths():
        relative = rel(path)
        if relative in FORBIDDEN_EXACT_FILES:
            errors.append(f"forbidden environment file shipped: {relative}")
            continue
        if path.name in FORBIDDEN_NAMES:
            errors.append(f"generated/cache artifact shipped: {relative}")
            continue
        if path.is_file() and path.suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"generated/cache file shipped: {relative}")


def check_secret_leaks(errors: list[str]) -> None:
    for path in iter_paths():
        if not path.is_file():
            continue
        relative = rel(path)
        if relative in ALLOWLIST_SECRET_FILES:
            continue
        if path.suffix not in SECRET_SCAN_EXTS and path.name not in {".npmrc", ".yarnrc"}:
            continue
        if path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            errors.append(f"cannot read {relative}: {exc}")
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret material in {relative}")
                break


def check_packaging_contract(errors: list[str]) -> None:
    package_json = ROOT / "frontend" / "package.json"
    lockfile = ROOT / "frontend" / "package-lock.json"
    if package_json.exists() and not lockfile.exists():
        errors.append("frontend/package.json exists but frontend/package-lock.json is missing")
    if package_json.exists():
        text = package_json.read_text(encoding="utf-8", errors="ignore")
        for needle in ["npm run typecheck", "npm run test:node", "next build", "node ./scripts/check-local-imports.mjs"]:
            if needle not in text:
                errors.append(f"frontend/package.json missing gate reference: {needle}")
    ci_script = ROOT / "scripts" / "validate_release_in_ci.sh"
    if ci_script.exists():
        text = ci_script.read_text(encoding="utf-8", errors="ignore")
        for needle in ["npm ci", "npm audit --audit-level", "npm run typecheck", "npm run build", "npm run test:node", "pip_audit", "pytest -q backend/tests"]:
            if needle not in text:
                errors.append(f"validate_release_in_ci.sh missing certification step: {needle}")


def main() -> int:
    errors: list[str] = []
    check_required(errors)
    check_forbidden_artifacts(errors)
    check_secret_leaks(errors)
    check_packaging_contract(errors)
    if errors:
        print("[artifact:fail] release artifact integrity check failed")
        for error in errors[:100]:
            print("-", error)
        if len(errors) > 100:
            print(f"- ... {len(errors) - 100} more")
        return 1
    print("[artifact:ok] required files, executable bits, clean tree and packaging contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
