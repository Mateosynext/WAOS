#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"
PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
  python backend/scripts/export_vertical_profiles.py \
  --profiles-dir frontend/app/lib/vertical-fallback/profiles \
  > frontend/app/lib/vertical-fallback/index.json
node -e "JSON.parse(require('fs').readFileSync('frontend/app/lib/vertical-fallback/index.json','utf8')); console.log('[vertical-profiles:ok] frontend fallback catalog synced')"
