#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p frontend/app/lib/vertical-fallback/profiles
python backend/scripts/export_vertical_profiles.py \
  --profiles-dir frontend/app/lib/vertical-fallback/profiles \
  > frontend/app/lib/vertical-fallback/index.json
printf '[vertical-sync:ok] frontend vertical fallback profiles synced\n'
