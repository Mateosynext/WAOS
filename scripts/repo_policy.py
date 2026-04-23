from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIR_NAMES = {"node_modules", ".next", ".git", ".venv", "venv", "__pycache__"}
FORBIDDEN_PATTERNS = [
    re.compile(r".*\.(bak|backup|old|orig|rej|tmp|temp|swp|swo|log)$", re.IGNORECASE),
    re.compile(r".*~$"),
    re.compile(r"(^|/)(notes\.txt|todo\.txt|scratch\.txt)$", re.IGNORECASE),
    re.compile(r"(^|/)\.notes(/|$)"),
    re.compile(r"(^|/)\.tmp(/|$)"),
    re.compile(r"(^|/)tmp(/|$)"),
    re.compile(r"(^|/)(playwright-report|test-results|coverage)(/|$)"),
    re.compile(r"(^|/)tsconfig\.tsbuildinfo$"),
    re.compile(r".*\.(db|sqlite|sqlite3|sqlite3-shm|sqlite3-wal)$", re.IGNORECASE),
]
EXPLICIT_ALLOWLIST = {
    Path("frontend/package-lock.json"),
}
DOC_REF_PATTERN = re.compile(r"(?P<ref>docs/[A-Za-z0-9_./-]+\.md)")
LEGACY_ROOT_LEAKS = [
    Path("backend/app/v8.py"),
]


def iter_source_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


def is_forbidden(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    rel_text = rel.as_posix()
    if rel in EXPLICIT_ALLOWLIST:
        return False
    if any(part in ALLOWED_DIR_NAMES for part in rel.parts):
        return False
    return any(pattern.search(rel_text) for pattern in FORBIDDEN_PATTERNS)


def collect_forbidden_files(root: Path) -> list[str]:
    offenders: list[str] = []
    for path in iter_source_files(root):
        if is_forbidden(path, root):
            offenders.append(path.relative_to(root).as_posix())
    return sorted(offenders)


def collect_missing_doc_refs(root: Path) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for markdown in sorted(root.rglob("*.md")):
        rel = markdown.relative_to(root)
        if any(part in ALLOWED_DIR_NAMES for part in rel.parts):
            continue
        text = markdown.read_text(encoding="utf-8", errors="ignore")
        seen_in_file: set[str] = set()
        for match in DOC_REF_PATTERN.finditer(text):
            ref = match.group("ref")
            if ref in seen_in_file:
                continue
            seen_in_file.add(ref)
            if not (root / ref).exists():
                missing.append({"source": rel.as_posix(), "reference": ref})
    return missing


def collect_legacy_root_leaks(root: Path) -> list[str]:
    return [path.as_posix() for path in LEGACY_ROOT_LEAKS if (root / path).exists()]


def scan_source_tree(root: Path) -> dict[str, object]:
    forbidden = collect_forbidden_files(root)
    missing_docs = collect_missing_doc_refs(root)
    legacy_leaks = collect_legacy_root_leaks(root)
    return {
        "forbidden_files": forbidden,
        "missing_doc_refs": missing_docs,
        "legacy_root_leaks": legacy_leaks,
        "ok": not forbidden and not missing_docs and not legacy_leaks,
    }
