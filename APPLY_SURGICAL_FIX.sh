#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
copy_file() {
  local rel="$1"
  mkdir -p "$ROOT/$(dirname "$rel")"
  cp "$(dirname "$0")/$rel" "$ROOT/$rel"
  echo "patched $rel"
}
copy_file backend/app/errors.py
copy_file backend/app/ai_workflows/bot_autopilot/schemas.py
copy_file backend/app/ai_workflows/bot_autopilot/service.py
copy_file backend/tests/test_ai_production_autopilot_v3_blindado_static.py
copy_file frontend/features/ai-command-center/AiCommandCenter.tsx
copy_file frontend/features/ai-command-center/types.ts
cp "$(dirname "$0")/AUTOPILOT_SURGICAL_FIX_2026-04-26.md" "$ROOT/AUTOPILOT_SURGICAL_FIX_2026-04-26.md"
echo "Surgical Autopilot fix applied. Run backend tests and redeploy."
