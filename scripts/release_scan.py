#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

LOCAL_DOMAIN_PATTERNS = [
    re.compile(r'localhost', re.IGNORECASE),
    re.compile(r'127\.0\.0\.1'),
    re.compile(r'(?<![./])\b[a-z0-9-]+\.local\b', re.IGNORECASE),
]
SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----'),
    re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}'),
]
PLACEHOLDER_PATTERNS = [
    re.compile(r'change-me', re.IGNORECASE),
    re.compile(r'replace-with', re.IGNORECASE),
    re.compile(r'your-backend', re.IGNORECASE),
    re.compile(r'set_[a-z0-9_]+_at_deploy', re.IGNORECASE),
    re.compile(r'generate_[a-z0-9_]+_at_deploy', re.IGNORECASE),
]
SKIP_DIRS = {'node_modules', '.next', '.git', '__pycache__', 'playwright-report', 'test-results'}
SKIP_LOCAL_DOMAIN_FILE_NAMES = {'.gitignore', '.dockerignore'}
ALLOWED_LOCAL_FILES = {
    'frontend/playwright.config.ts',
    'frontend/playwright.mocked.config.ts',
    'frontend/playwright.real.config.ts',
    'frontend/playwright.shared.ts',
    'frontend/tests/e2e/mock-api-server.mjs',
    'frontend/tests/e2e/agenda-payments-multiorg.real.spec.ts',
    'frontend/tests/e2e/helpers.real.ts',
    'frontend/tests/e2e/login-mfa.mock.spec.ts',
    'backend/scripts/preflight_check.py',
    'backend/scripts/run_browser_e2e_server.py',
    'scripts/runtime_artifact_smoke.py',
}
SKIP_SCAN_FILES = {'scripts/release_scan.py'}


def iter_files(base: Path):
    for path in sorted(base.rglob('*')):
        if path.is_dir():
            continue
        rel = path.relative_to(base).as_posix()
        parts = set(rel.split('/'))
        if parts & SKIP_DIRS:
            continue
        yield path, rel


def _resolve_base(base: Path) -> Path:
    children = [child for child in base.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return base


def inspect(base: Path, fail_on_placeholder: bool) -> dict[str, object]:
    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    for path, rel in iter_files(base):
        if rel in SKIP_SCAN_FILES:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                errors.append({'type': 'secret', 'file': rel, 'match': match.group(0)[:80]})
        if rel not in ALLOWED_LOCAL_FILES and path.name not in SKIP_LOCAL_DOMAIN_FILE_NAMES:
            for pattern in LOCAL_DOMAIN_PATTERNS:
                for match in pattern.finditer(text):
                    errors.append({'type': 'local_domain', 'file': rel, 'match': match.group(0)})
        for pattern in PLACEHOLDER_PATTERNS:
            for match in pattern.finditer(text):
                entry = {'type': 'placeholder', 'file': rel, 'match': match.group(0)}
                if rel.endswith('.example') and not fail_on_placeholder:
                    warnings.append(entry)
                else:
                    errors.append(entry)
    return {'ok': not errors, 'errors': errors, 'warnings': warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description='Scan release content for secrets, placeholders, and local domains.')
    parser.add_argument('target', help='Directory or zip artifact to scan')
    parser.add_argument('--report', help='Optional JSON report path')
    parser.add_argument('--fail-on-placeholder', action='store_true')
    args = parser.parse_args()

    target = Path(args.target)
    temp_dir: str | None = None
    try:
        if target.suffix.lower() == '.zip':
            temp_dir = tempfile.mkdtemp(prefix='waos-release-scan-')
            with zipfile.ZipFile(target, 'r') as zf:
                zf.extractall(temp_dir)
            base = _resolve_base(Path(temp_dir))
        else:
            base = target
        report = inspect(base, fail_on_placeholder=args.fail_on_placeholder)
        if args.report:
            Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report['ok'] else 1
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
