#!/usr/bin/env python3
"""Normalize executable bits required by WAOS release/deploy gates.

Some ZIP upload paths and repository migrations can drop POSIX executable bits
from shell scripts even when the file contents are correct. This script repairs
only the small allowlisted set of release scripts before the integrity gate runs,
then reports the normalized modes for auditability.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXECUTABLE_FILES = (
    "scripts/validate_release_in_ci.sh",
    "scripts/validate_zip_reproducible.sh",
    "backend/scripts/run_ci_checks.sh",
)


def _mode_string(path: Path) -> str:
    return stat.filemode(path.stat().st_mode)


def main() -> int:
    changed: list[str] = []
    missing: list[str] = []
    for rel in EXECUTABLE_FILES:
        path = ROOT / rel
        if not path.is_file():
            missing.append(rel)
            continue
        current_mode = path.stat().st_mode
        desired_mode = current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if current_mode != desired_mode:
            os.chmod(path, desired_mode)
            changed.append(rel)

    if missing:
        print("[perms:fail] missing executable release files:")
        for rel in missing:
            print(f"- {rel}")
        return 1

    status = "updated" if changed else "already-ok"
    print(f"[perms:{status}] normalized executable release files={len(EXECUTABLE_FILES)}")
    for rel in EXECUTABLE_FILES:
        print(f"[perms:mode] {_mode_string(ROOT / rel)} {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
