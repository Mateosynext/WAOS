#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISALLOWED_LICENSE_PATTERNS = (r'(^|[^A-Z])AGPL([^A-Z]|$)', r'(^|[^A-Z])SSPL([^A-Z]|$)', r'(^|[^A-Z])BUSL([^A-Z]|$)', r'(^|[^A-Z])GPL-3\.0-only([^A-Z]|$)', r'(^|[^A-Z])GPL-3\.0([^A-Z]|$)')
WARN_LICENSE_SNIPPETS = ('LGPL', 'MPL', 'CDDL', 'EPL')


def parse_requirements(path: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        req = re.split(r'[;#]', line, maxsplit=1)[0].strip()
        name = re.split(r'[<>=!\[]', req, maxsplit=1)[0].strip()
        items.append({'name': name, 'specifier': req})
    return items


def safe_license(dist_name: str) -> tuple[str | None, str | None]:
    try:
        md = metadata(dist_name)
        declared = md.get('License')
        if declared and declared.strip() and declared.strip().upper() != 'UNKNOWN':
            return version(dist_name), declared.strip()
        classifiers = [v.split('::')[-1].strip() for k, v in md.items() if k == 'Classifier' and 'License ::' in v]
        if classifiers:
            return version(dist_name), '; '.join(classifiers)
        return version(dist_name), None
    except PackageNotFoundError:
        return None, None


def parse_frontend_lock(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding='utf-8'))
    packages = data.get('packages', {})
    items: list[dict[str, object]] = []
    for package_path, meta in sorted(packages.items()):
        if not package_path.startswith('node_modules/'):
            continue
        name = package_path.split('node_modules/', 1)[1]
        items.append({
            'name': name,
            'version': meta.get('version'),
            'license': meta.get('license'),
            'resolved': meta.get('resolved'),
            'dev': bool(meta.get('dev', False)),
            'optional': bool(meta.get('optional', False)),
        })
    return items


def evaluate_licenses(frontend: list[dict[str, object]], backend: list[dict[str, object]]) -> dict[str, object]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def classify(source: str, name: str, license_value: str | None) -> None:
        if not license_value:
            warnings.append({'source': source, 'name': name, 'issue': 'license_unknown'})
            return
        upper = license_value.upper()
        if any(re.search(pattern, upper) for pattern in DISALLOWED_LICENSE_PATTERNS):
            errors.append({'source': source, 'name': name, 'license': license_value, 'issue': 'disallowed_license'})
        elif any(snippet in upper for snippet in WARN_LICENSE_SNIPPETS):
            warnings.append({'source': source, 'name': name, 'license': license_value, 'issue': 'copyleft_or_restricted_review'})

    for item in frontend:
        classify('frontend', str(item['name']), item.get('license'))
    for item in backend:
        classify('backend', str(item['name']), item.get('license'))

    return {
        'ok': not errors,
        'policy': {
            'disallowed_license_patterns': list(DISALLOWED_LICENSE_PATTERNS),
            'warning_license_snippets': list(WARN_LICENSE_SNIPPETS),
        },
        'errors': errors,
        'warnings': warnings,
        'summary': {
            'frontend_packages': len(frontend),
            'backend_dependencies': len(backend),
            'errors': len(errors),
            'warnings': len(warnings),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate SBOM-like dependency inventory and license audit for WAOS release.')
    parser.add_argument('--sbom-out', required=True)
    parser.add_argument('--license-out', required=True)
    args = parser.parse_args()

    backend_deps = parse_requirements(ROOT / 'backend/requirements.txt')
    backend_inventory = []
    for item in backend_deps:
        resolved_version, license_value = safe_license(item['name'])
        backend_inventory.append({
            'name': item['name'],
            'specifier': item['specifier'],
            'resolved_version_if_available': resolved_version,
            'license': license_value,
        })

    frontend_inventory = parse_frontend_lock(ROOT / 'frontend/package-lock.json')
    sbom = {
        'sbom_format': 'waos-dependency-inventory/v1',
        'app_version': json.loads((ROOT / 'frontend/package.json').read_text(encoding='utf-8'))['version'],
        'backend': backend_inventory,
        'frontend': frontend_inventory,
    }
    Path(args.sbom_out).write_text(json.dumps(sbom, indent=2, ensure_ascii=False), encoding='utf-8')

    license_audit = evaluate_licenses(frontend_inventory, backend_inventory)
    Path(args.license_out).write_text(json.dumps(license_audit, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'sbom': args.sbom_out, 'license_audit': args.license_out, 'license_ok': license_audit['ok']}, indent=2, ensure_ascii=False))
    return 0 if license_audit['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
