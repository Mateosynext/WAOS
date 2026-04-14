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
MANIFEST_SCHEMA_VERSION = 'waos-release-manifest/v2'
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
]


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


def ensure_runtime_placeholders(runtime_root: Path) -> None:
    placeholder_dirs = [runtime_root / 'backend/app/artifacts/reports']
    for directory in placeholder_dirs:
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


def write_checksums(dist_dir: Path, artifacts: list[Path]) -> Path:
    output = dist_dir / 'RELEASE_CHECKSUMS.sha256'
    lines = [f'{sha256(path)}  {path.name}' for path in artifacts]
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output


def write_manifest(dist_dir: Path, runtime_dir: Path, docs_dir: Path, source_dir: Path, runtime_zip: Path, docs_zip: Path, source_zip: Path, checksums_path: Path, reports: dict[str, Path]) -> Path:
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
        'separation_policy': {
            'runtime': 'Deployable backend/frontend only. Excludes docs, tests, CI helpers, and local build artifacts.',
            'audit_docs': 'Audit evidence, release notes, reports, SBOM, license verification, and reproducibility documentation.',
            'source': 'Updated WAOS source with release tooling, CI validation, and vertical portfolio integration.',
        },
    }
    manifest_path = dist_dir / 'RELEASE_MANIFEST.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    (dist_dir / 'RELEASE_MANIFEST.sha256').write_text(f'{sha256(manifest_path)}  {manifest_path.name}\n', encoding='utf-8')
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Build clean WAOS runtime and audit release artifacts.')
    parser.add_argument('--output-dir', default=str(DEFAULT_DIST))
    args = parser.parse_args()

    validate_root_name()
    dist_dir = Path(args.output_dir)
    reports_dir = dist_dir / 'reports'
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    runtime_dir = dist_dir / RUNTIME_NAME
    docs_dir = dist_dir / DOCS_NAME
    source_dir = dist_dir / SOURCE_NAME
    runtime_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    copy_selected(ROOT, runtime_dir, TOP_LEVEL_RUNTIME, RUNTIME_EXCLUDES)
    ensure_runtime_placeholders(runtime_dir)
    write_artifact_profile(runtime_dir, 'runtime')

    copy_selected(ROOT, docs_dir, AUDIT_DOCS, [])
    write_artifact_profile(docs_dir, 'audit_docs')

    copy_selected(ROOT, source_dir, [item.name for item in ROOT.iterdir() if item.name != 'dist'], SOURCE_EXCLUDES)
    write_artifact_profile(source_dir, 'source')

    runtime_zip = dist_dir / f'{RUNTIME_NAME}.zip'
    docs_zip = dist_dir / f'{DOCS_NAME}.zip'
    source_zip = dist_dir / f'{SOURCE_NAME}.zip'
    zip_dir(runtime_dir, runtime_zip)

    gate_report = reports_dir / 'runtime_gate_report.json'
    scan_report = reports_dir / 'runtime_scan_report.json'
    sbom_report = reports_dir / 'sbom_inventory.json'
    license_report = reports_dir / 'dependency_license_audit.json'
    smoke_report = reports_dir / 'runtime_smoke_report.json'

    run([sys.executable, 'scripts/release_gate.py', str(runtime_zip), '--profile', 'runtime', '--expected-root-name', RUNTIME_NAME, '--report', str(gate_report)])
    run([sys.executable, 'scripts/release_scan.py', str(runtime_zip), '--fail-on-placeholder', '--report', str(scan_report)])
    run([sys.executable, 'scripts/generate_release_metadata.py', '--sbom-out', str(sbom_report), '--license-out', str(license_report)])
    run([sys.executable, 'scripts/runtime_artifact_smoke.py', str(runtime_zip), '--report', str(smoke_report)])

    for report in [gate_report, scan_report, sbom_report, license_report, smoke_report]:
        shutil.copy2(report, docs_dir / report.name)

    zip_dir(docs_dir, docs_zip)
    zip_dir(source_dir, source_zip)

    checksums_path = write_checksums(dist_dir, [runtime_zip, docs_zip, source_zip])
    reports = {
        'runtime_gate': gate_report,
        'runtime_scan': scan_report,
        'sbom_inventory': sbom_report,
        'dependency_license_audit': license_report,
        'runtime_smoke': smoke_report,
    }
    manifest_path = write_manifest(dist_dir, runtime_dir, docs_dir, source_dir, runtime_zip, docs_zip, source_zip, checksums_path, reports)

    print(json.dumps({
        'runtime_zip': str(runtime_zip),
        'audit_docs_zip': str(docs_zip),
        'source_zip': str(source_zip),
        'manifest': str(manifest_path),
        'checksums': str(checksums_path),
        'reports': [str(gate_report), str(scan_report), str(sbom_report), str(license_report), str(smoke_report)],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
