#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 path/to/waos-release.zip" >&2
  exit 2
fi

ZIP_PATH="$1"
if [[ ! -f "$ZIP_PATH" ]]; then
  echo "[zip:fail] not found: $ZIP_PATH" >&2
  exit 2
fi

TMP_ROOT="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

EXTRACT_DIR="$TMP_ROOT/extracted"
mkdir -p "$EXTRACT_DIR"

ZIP_ABS="$(cd "$(dirname "$ZIP_PATH")" && pwd)/$(basename "$ZIP_PATH")"
"${PYTHON_BIN:-/usr/bin/python3}" - "$ZIP_ABS" "$EXTRACT_DIR" <<'PYZIP'
from __future__ import annotations

import os
import stat
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1]).resolve()
out_dir = Path(sys.argv[2]).resolve()
max_members = int(os.environ.get("WAOS_ZIP_MAX_MEMBERS", "5000"))
max_total = int(os.environ.get("WAOS_ZIP_MAX_TOTAL_BYTES", "250000000"))
max_file = int(os.environ.get("WAOS_ZIP_MAX_FILE_BYTES", "50000000"))

with zipfile.ZipFile(zip_path) as zf:
    infos = zf.infolist()
    if len(infos) > max_members:
        raise SystemExit(f"[zip:fail] too many ZIP members: {len(infos)} > {max_members}")
    total = 0
    seen = set()
    for info in infos:
        name = info.filename
        if not name or name.endswith("/"):
            continue
        target = (out_dir / name).resolve()
        if not str(target).startswith(str(out_dir) + os.sep):
            raise SystemExit(f"[zip:fail] unsafe path traversal member: {name}")
        if name.startswith("/") or "\x00" in name:
            raise SystemExit(f"[zip:fail] unsafe member name: {name!r}")
        mode = (info.external_attr >> 16) & 0o170000
        if mode in {stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK}:
            raise SystemExit(f"[zip:fail] unsupported special file in ZIP: {name}")
        key = name.rstrip("/")
        if key in seen:
            raise SystemExit(f"[zip:fail] duplicate ZIP member: {name}")
        seen.add(key)
        total += info.file_size
        if info.file_size > max_file:
            raise SystemExit(f"[zip:fail] ZIP member too large: {name} ({info.file_size} bytes)")
        if total > max_total:
            raise SystemExit(f"[zip:fail] ZIP expands beyond limit: {total} bytes")
    zf.extractall(out_dir)
print(f"[zip:ok] safe extraction members={len(infos)} bytes={total}")
PYZIP
chmod -R u+rwX "$EXTRACT_DIR"

SOURCE_ROOT="$EXTRACT_DIR"
if [[ ! -x "$SOURCE_ROOT/scripts/validate_release_in_ci.sh" && ! -f "$SOURCE_ROOT/scripts/validate_release_in_ci.sh" ]]; then
  mapfile -t dirs < <(find "$EXTRACT_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
  if [[ ${#dirs[@]} -eq 1 && -f "${dirs[0]}/scripts/validate_release_in_ci.sh" ]]; then
    SOURCE_ROOT="${dirs[0]}"
  fi
fi

if [[ ! -f "$SOURCE_ROOT/scripts/validate_release_in_ci.sh" ]]; then
  echo "[zip:fail] ZIP does not contain scripts/validate_release_in_ci.sh at the root or one top-level directory" >&2
  exit 1
fi

mapfile -t shipped_artifacts < <(find "$SOURCE_ROOT" \
  \( -path '*/node_modules' -o -path '*/.next' -o -path '*/__pycache__' -o -path '*/.pytest_cache' -o -name '*.pyc' -o -name '*.pyo' -o -name '*.tsbuildinfo' \) \
  -print | sort | head -50)
if [[ ${#shipped_artifacts[@]} -gt 0 ]]; then
  echo "[zip:fail] ZIP ships generated/cache artifacts:" >&2
  printf ' - %s\n' "${shipped_artifacts[@]}" >&2
  exit 1
fi

cd "$SOURCE_ROOT"
echo "[zip:run] validating extracted ZIP at $SOURCE_ROOT"
bash scripts/validate_release_in_ci.sh
echo "[zip:ok] extracted ZIP validation passed"
