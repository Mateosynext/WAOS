#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_checksums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        values[name.strip()] = digest.strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify release artifact hashes against the manifest and checksum file.')
    parser.add_argument('manifest')
    parser.add_argument('--checksums', required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    checksums_path = Path(args.checksums).resolve()
    dist_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    checksums = parse_checksums(checksums_path)

    failures: list[dict[str, str]] = []
    for key in ('runtime_zip', 'audit_docs_zip', 'source_zip'):
        entry = manifest['artifacts'][key]
        artifact = dist_dir / entry['path']
        actual = sha256(artifact)
        if actual != entry['sha256']:
            failures.append({'artifact': entry['path'], 'expected': entry['sha256'], 'actual': actual, 'source': 'manifest'})
        checksum_actual = checksums.get(entry['path'])
        if checksum_actual != actual:
            failures.append({'artifact': entry['path'], 'expected': checksum_actual or '', 'actual': actual, 'source': 'checksums'})

    report = {'ok': not failures, 'failures': failures}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
