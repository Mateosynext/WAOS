#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / 'dist'
VERSION = json.loads((ROOT / 'frontend/package.json').read_text(encoding='utf-8'))['version']
RELEASE_ID = f'{VERSION}-clean-release'
RUNTIME_NAME = f'waos_runtime_{RELEASE_ID}'
DOCS_NAME = f'waos_audit_docs_{RELEASE_ID}'
SOURCE_NAME = f'waos_source_{RELEASE_ID}'
MANIFEST_SCHEMA_VERSION = 'waos-release-manifest/v3'
TOP_LEVEL_RUNTIME = ['README.md', 'DEPLOY.md', 'backend', 'frontend']
AUDIT_DOCS = [
    'POSTGRESQL_RELEASE_NOTE.md',
    'README.md',
    'RELEASE_NOTES_BLOCK1.md',
    'RELEASE_NOTES_BLOCK10_E2E_VALUATION.md',
    'RELEASE_NOTES_BLOCK2.md',
    'RELEASE_NOTES_BLOCK3.md',
    'RELEASE_NOTES_BLOCK4.md',
    'RELEASE_NOTES_BLOCK5.md',
    'RELEASE_NOTES_BLOCK6.md',
    'RELEASE_NOTES_BLOCK7.md',
    'RELEASE_NOTES_BLOCK8_SECURITY.md',
    'RELEASE_NOTES_BLOCK9_QA_OPERATIVO.md',
    'RELEASE_NOTES_FINAL_UNIFICADA.md',
    'SECURITY_PRE_RELEASE_CHECKLIST.md',
    'VALIDATION_BLOCK10_E2E.md',
    'VALIDATION_FINAL_REPORT.md',
    'VERTICALES_IMPLEMENTADAS.md',
    'docs/WAOS_VERTICAL_PORTFOLIO.md',
    'docs/RELEASE_REPRODUCIBILITY.md',
]
RUNTIME_EXCLUDES = [
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyo',
    '**/*.db',
    '**/*.sqlite',
    '**/*.sqlite3',
    '**/*.sqlite3-shm',
    '**/*.sqlite3-wal',
    '**/*.tsbuildinfo',
    '**/.env',
    '**/.env.local',
    '**/.env.development.local',
    '**/.env.test.local',
    '**/.env.production.local',
    '**/node_modules/**',
    '**/.next/**',
    '**/playwright-report/**',
    '**/test-results/**',
    '**/coverage/**',
    '**/.pytest_cache/**',
    'backend/tests/**',
    'backend/scripts/**',
    'frontend/tests/**',
    'frontend/scripts/**',
    'frontend/playwright*.ts',
    'backend/app/artifacts/reports/**',
    'docs/**',
    'scripts/**',
    '.github/**',
    'RELEASE_NOTES_*.md',
    'VALIDATION_*.md',
    'SECURITY_PRE_RELEASE_CHECKLIST.md',
    'VERTICALES_IMPLEMENTADAS.md',
    'POSTGRESQL_RELEASE_NOTE.md',
    'ARCHITECTURE_REFACTOR_NOTES.md',
    'WAOS_*REPORT*.txt',
]
SOURCE_EXCLUDES = [
    'dist/**',
    '.git/**',
    '**/__pycache__',
    '**/*.pyc',
    '**/*.pyo',
    '**/*.db',
    '**/*.sqlite',
    '**/*.sqlite3',
    '**/*.sqlite3-shm',
    '**/*.sqlite3-wal',
    '**/*.tsbuildinfo',
    '**/.env',
    '**/.env.local',
    '**/.env.development.local',
    '**/.env.test.local',
    '**/.env.production.local',
    '**/node_modules/**',
    '**/.next/**',
    '**/playwright-report/**',
    '**/test-results/**',
    '**/coverage/**',
    '**/.pytest_cache/**',
    'backend/app/artifacts/reports/**',
]

FORBIDDEN_SOURCE_PATTERNS = {
    'sqlite_databases': ['*.db', '*.sqlite', '*.sqlite3', '*.sqlite3-shm', '*.sqlite3-wal'],
    'typescript_buildinfo': ['*.tsbuildinfo'],
    'generated_reports': ['backend/app/artifacts/reports/*.pdf'],
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def validate_root_name() -> None:
    if ROOT.name.startswith('waos_') and ROOT.name != SOURCE_NAME:
        raise SystemExit(
            f'Root directory name mismatch: expected {SOURCE_NAME!r} for version {VERSION}, got {ROOT.name!r}. '
            'Rename the extracted source folder before building the release.'
        )


def should_exclude(rel: Path, patterns: list[str]) -> bool:
    rel_posix = rel.as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(rel_posix, pattern):
            return True
        if pattern.endswith('/**'):
            prefix = pattern[:-3].rstrip('/')
            if rel_posix == prefix or rel_posix.startswith(prefix + '/'):
                return True
    return False


def copy_tree(src: Path, dst: Path, patterns: list[str], entry_name: str | None = None) -> int:
    count = 0
    for path in sorted(src.rglob('*')):
        rel = path.relative_to(src)
        rel_for_filter = Path(entry_name) / rel if entry_name else rel
        if should_exclude(rel_for_filter, patterns):
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            count += 1
    return count


def copy_selected(src_root: Path, dst_root: Path, entries: list[str], patterns: list[str]) -> int:
    copied = 0
    for entry in entries:
        src = src_root / entry
        if src.is_dir():
            copied += copy_tree(src, dst_root / entry, patterns, entry_name=entry)
        elif src.is_file() and not should_exclude(Path(entry), patterns):
            target = dst_root / entry
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied += 1
    return copied


def ensure_placeholder_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    gitkeep = directory / '.gitkeep'
    gitkeep.touch(exist_ok=True)
    for child in list(directory.iterdir()):
        if child.name == '.gitkeep':
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def ensure_runtime_placeholders(runtime_root: Path) -> None:
    ensure_placeholder_dir(runtime_root / 'backend/app/artifacts/reports')


def ensure_source_hygiene(source_root: Path) -> None:
    ensure_placeholder_dir(source_root / 'backend/app/artifacts/reports')


def write_artifact_profile(artifact_root: Path, profile: str) -> None:
    payload = {
        'profile': profile,
        'release_id': RELEASE_ID,
        'app_version': VERSION,
        'generated_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'root_directory': artifact_root.name,
    }
    (artifact_root / 'ARTIFACT_PROFILE.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def zip_dir(src: Path, dest_zip: Path) -> None:
    with ZipFile(dest_zip, 'w', compression=ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob('*')):
            if path.is_dir():
                continue
            zf.write(path, path.relative_to(src.parent).as_posix())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def count_files(path: Path) -> int:
    return sum(1 for p in path.rglob('*') if p.is_file())


def collect_matches(base: Path, patterns: dict[str, list[str]]) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {key: [] for key in patterns}
    for path in sorted(base.rglob('*')):
        if path.is_dir():
            continue
        rel = path.relative_to(base).as_posix()
        for key, key_patterns in patterns.items():
            if any(fnmatch.fnmatch(rel, pattern) for pattern in key_patterns):
                matches[key].append(rel)
    return {key: value for key, value in matches.items() if value}


def build_size_report(source_root: Path, runtime_zip: Path, docs_zip: Path, source_zip: Path) -> dict[str, object]:
    source_files = sorted((p.stat().st_size, p.relative_to(source_root).as_posix()) for p in source_root.rglob('*') if p.is_file())
    top_removed = [
        {'path': rel, 'size_bytes': size, 'size_kb': round(size / 1024, 1)}
        for size, rel in source_files[-10:][::-1]
        if rel.endswith('.db') or rel.endswith('.pdf') or rel.endswith('.tsbuildinfo')
    ]
    original_size = sum(size for size, _ in source_files)
    zipped_size = source_zip.stat().st_size
    return {
        'source_tree_size_bytes': original_size,
        'source_zip_size_bytes': zipped_size,
        'runtime_zip_size_bytes': runtime_zip.stat().st_size,
        'audit_docs_zip_size_bytes': docs_zip.stat().st_size,
        'top_local_or_generated_files_removed': top_removed,
    }


def write_checksums(dist_dir: Path, artifacts: list[Path]) -> Path:
    output = dist_dir / 'RELEASE_CHECKSUMS.sha256'
    lines = [f'{sha256(path)}  {path.name}' for path in artifacts]
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output


def write_manifest(dist_dir: Path, runtime_dir: Path, docs_dir: Path, source_dir: Path, runtime_zip: Path, docs_zip: Path, source_zip: Path, checksums_path: Path, reports: dict[str, Path], hygiene: dict[str, object], size_report: dict[str, object]) -> Path:
    manifest = {
        'manifest_schema_version': MANIFEST_SCHEMA_VERSION,
        'release_version': RELEASE_ID,
        'app_version': VERSION,
        'generated_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'builder': {
            'tool': 'scripts/release_build.py',
            'source_root_name': ROOT.name,
        },
        'artifacts': {
            'runtime_zip': {
                'profile': 'runtime',
                'path': runtime_zip.name,
                'sha256': sha256(runtime_zip),
                'file_count': count_files(runtime_dir),
            },
            'audit_docs_zip': {
                'profile': 'audit_docs',
                'path': docs_zip.name,
                'sha256': sha256(docs_zip),
                'file_count': count_files(docs_dir),
            },
            'source_zip': {
                'profile': 'source',
                'path': source_zip.name,
                'sha256': sha256(source_zip),
                'file_count': count_files(source_dir),
            },
            'checksums': {
                'path': checksums_path.name,
                'sha256': sha256(checksums_path),
            },
        },
        'reports': {key: {'path': path.name, 'sha256': sha256(path)} for key, path in reports.items()},
        'exclusions_applied': {
            'runtime': RUNTIME_EXCLUDES,
            'source': SOURCE_EXCLUDES,
        },
        'hygiene': hygiene,
        'size_report': size_report,
        'separation_policy': {
            'runtime': 'Deployable backend/frontend only. Excludes docs, tests, CI helpers, local databases, generated reports, and local build artifacts.',
            'audit_docs': 'Audit evidence, release notes, reports, SBOM, license verification, and reproducibility documentation.',
            'source': 'Updated WAOS source with release tooling, CI validation, and sanitized placeholders for local/generated runtime artifacts.',
        },
    }
    manifest_path = dist_dir / 'RELEASE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (dist_dir / 'RELEASE_MANIFEST.sha256').write_text(f'{sha256(manifest_path)}  {manifest_path.name}\n', encoding='utf-8')
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Build WAOS release artifacts.')
    parser.add_argument('--output-dir', default=str(DEFAULT_DIST))
    args = parser.parse_args()

    validate_root_name()
    dist_dir = Path(args.output_dir).resolve()
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    hygiene_hits = collect_matches(ROOT, FORBIDDEN_SOURCE_PATTERNS)
    hygiene_report = {
        'source_tree_forbidden_hits': hygiene_hits,
        'source_tree_clean': not hygiene_hits,
    }

    runtime_dir = dist_dir / RUNTIME_NAME
    docs_dir = dist_dir / DOCS_NAME
    source_dir = dist_dir / SOURCE_NAME

    copy_selected(ROOT, runtime_dir, TOP_LEVEL_RUNTIME, RUNTIME_EXCLUDES)
    ensure_runtime_placeholders(runtime_dir)
    write_artifact_profile(runtime_dir, 'runtime')

    copy_selected(ROOT, docs_dir, AUDIT_DOCS, [])
    write_artifact_profile(docs_dir, 'audit_docs')

    copy_tree(ROOT, source_dir, SOURCE_EXCLUDES)
    ensure_source_hygiene(source_dir)
    write_artifact_profile(source_dir, 'source')

    runtime_zip = dist_dir / f'{RUNTIME_NAME}.zip'
    docs_zip = dist_dir / f'{DOCS_NAME}.zip'
    source_zip = dist_dir / f'{SOURCE_NAME}.zip'
    zip_dir(runtime_dir, runtime_zip)
    zip_dir(docs_dir, docs_zip)
    zip_dir(source_dir, source_zip)

    size_report = build_size_report(ROOT, runtime_zip, docs_zip, source_zip)
    size_report_path = dist_dir / 'ARTIFACT_SIZES.json'
    size_report_path.write_text(json.dumps(size_report, indent=2, ensure_ascii=False), encoding='utf-8')

    checksums_path = write_checksums(dist_dir, [runtime_zip, docs_zip, source_zip, size_report_path])

    reports = {'artifact_sizes': size_report_path}
    manifest_path = write_manifest(dist_dir, runtime_dir, docs_dir, source_dir, runtime_zip, docs_zip, source_zip, checksums_path, reports, hygiene_report, size_report)

    print(json.dumps({
        'ok': True,
        'release_id': RELEASE_ID,
        'dist_dir': str(dist_dir),
        'runtime_zip': runtime_zip.name,
        'docs_zip': docs_zip.name,
        'source_zip': source_zip.name,
        'manifest': manifest_path.name,
        'size_report': size_report_path.name,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
