#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

FORBIDDEN_RUNTIME_PATTERNS = {
    'sqlite_databases': ['*.db', '*.sqlite', '*.sqlite3'],
    'python_bytecode': ['*.pyc', '*.pyo'],
    'python_cache_dirs': ['__pycache__'],
    'ts_buildinfo': ['*.tsbuildinfo'],
    'local_env_files': ['.env', '.env.local', '.env.development.local', '.env.test.local', '.env.production.local'],
    'test_artifacts': ['playwright-report', 'test-results', 'coverage', '.pytest_cache'],
    'local_build_dirs': ['node_modules', '.next'],
}


def _iter_paths(base: Path) -> list[str]:
    items: list[str] = []
    for item in sorted(base.rglob('*')):
        rel = item.relative_to(base).as_posix()
        items.append(rel + '/' if item.is_dir() else rel)
    return items


def _matches(name: str, patterns: list[str]) -> bool:
    path = Path(name.rstrip('/'))
    lowered = name.lower()
    for pattern in patterns:
        if pattern in {'__pycache__', 'playwright-report', 'test-results', 'coverage', '.pytest_cache', 'node_modules', '.next'}:
            if pattern.lower() in lowered.strip('/').split('/'):
                return True
        elif path.match(pattern) or path.name == pattern:
            return True
    return False


def _resolve_base(base: Path) -> tuple[Path, str]:
    children = [child for child in base.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0], children[0].name
    return base, base.name


def scan(base: Path, profile: str, root_name: str, expected_root_name: str | None) -> dict[str, object]:
    hits: dict[str, list[str]] = {key: [] for key in FORBIDDEN_RUNTIME_PATTERNS}
    runtime_only: list[str] = []
    naming: list[str] = []
    for rel in _iter_paths(base):
        clean = rel.rstrip('/')
        for key, patterns in FORBIDDEN_RUNTIME_PATTERNS.items():
            if _matches(clean, patterns):
                hits[key].append(rel)
        if profile == 'runtime':
            if clean.startswith('backend/tests/') or clean.startswith('frontend/tests/'):
                runtime_only.append(rel)
            elif clean.startswith('backend/scripts/') or clean.startswith('frontend/scripts/'):
                runtime_only.append(rel)
            elif clean.startswith('docs/'):
                runtime_only.append(rel)
            elif clean.startswith('RELEASE_NOTES_') or clean.startswith('VALIDATION_'):
                runtime_only.append(rel)
            elif clean.startswith('.github/') or clean.startswith('scripts/'):
                runtime_only.append(rel)
            elif clean.startswith('frontend/playwright'):
                runtime_only.append(rel)
            elif clean in {'SECURITY_PRE_RELEASE_CHECKLIST.md', 'VERTICALES_IMPLEMENTADAS.md', 'POSTGRESQL_RELEASE_NOTE.md', 'ARCHITECTURE_REFACTOR_NOTES.md'}:
                runtime_only.append(rel)
    if expected_root_name and root_name != expected_root_name:
        naming.append(f'expected root {expected_root_name}, got {root_name}')
    failures = {k: v for k, v in hits.items() if v}
    if runtime_only:
        failures['runtime_docs_or_tests'] = runtime_only
    if naming:
        failures['root_name_mismatch'] = naming
    return {
        'profile': profile,
        'root_name': root_name,
        'expected_root_name': expected_root_name,
        'ok': not failures,
        'failures': failures,
        'counts': {k: len(v) for k, v in failures.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Fail release validation when forbidden artifacts are present.')
    parser.add_argument('target', help='Directory or zip artifact to validate')
    parser.add_argument('--profile', choices=['runtime', 'source'], default='runtime')
    parser.add_argument('--expected-root-name')
    parser.add_argument('--report', help='Optional JSON report path')
    args = parser.parse_args()

    target = Path(args.target)
    temp_dir: str | None = None
    try:
        if target.suffix.lower() == '.zip':
            temp_dir = tempfile.mkdtemp(prefix='waos-release-gate-')
            with zipfile.ZipFile(target, 'r') as zf:
                zf.extractall(temp_dir)
            base, root_name = _resolve_base(Path(temp_dir))
        else:
            base = target
            root_name = target.name
        report = scan(base, args.profile, root_name, args.expected_root_name)
        if args.report:
            Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report['ok'] else 1
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
