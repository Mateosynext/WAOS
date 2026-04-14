#!/usr/bin/env bash
set -euo pipefail

python scripts/release_build.py --output-dir dist
RUNTIME_ZIP=$(find dist -maxdepth 1 -type f -name 'waos_runtime_*-clean-release.zip' | sort | tail -n 1)
DOCS_ZIP=$(find dist -maxdepth 1 -type f -name 'waos_audit_docs_*-clean-release.zip' | sort | tail -n 1)
SOURCE_ZIP=$(find dist -maxdepth 1 -type f -name 'waos_source_*-clean-release.zip' | sort | tail -n 1)
MANIFEST=dist/RELEASE_MANIFEST.json
CHECKSUMS=dist/RELEASE_CHECKSUMS.sha256

for path in "$RUNTIME_ZIP" "$DOCS_ZIP" "$SOURCE_ZIP" "$MANIFEST" "$CHECKSUMS"; do
  if [ -z "${path:-}" ] || [ ! -e "$path" ]; then
    echo "Missing expected release artifact: $path" >&2
    exit 1
  fi
done

python scripts/verify_release_hashes.py "$MANIFEST" --checksums "$CHECKSUMS"
