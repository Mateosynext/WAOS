#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIR_NAMES = {"node_modules", ".next", ".git", ".venv", "venv", "__pycache__"}
FORBIDDEN_PATTERNS = [
    re.compile(r".*\.(bak|backup|old|orig|rej|tmp|temp|swp|swo)$", re.IGNORECASE),
    re.compile(r".*~$"),
    re.compile(r"(^|/)(notes\.txt|todo\.txt|scratch\.txt)$", re.IGNORECASE),
    re.compile(r"(^|/)\.notes(/|$)"),
    re.compile(r"(^|/)tmp(/|$)"),
]
EXPLICIT_ALLOWLIST = {
    Path('frontend/package-lock.json'),
}


def is_forbidden(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_text = rel.as_posix()
    if rel in EXPLICIT_ALLOWLIST:
        return False
    if any(part in ALLOWED_DIR_NAMES for part in rel.parts):
        return False
    return any(pattern.search(rel_text) for pattern in FORBIDDEN_PATTERNS)


def main() -> int:
    offenders: list[str] = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if is_forbidden(path):
            offenders.append(path.relative_to(ROOT).as_posix())
    if offenders:
        print('Repo hygiene check failed. Remove these files before commit:', file=sys.stderr)
        for item in sorted(offenders):
            print(f' - {item}', file=sys.stderr)
        return 1
    print('Repo hygiene check passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
