#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN="${1:-}"

remove_target() {
  local target="$1"
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    printf '[dry-run] %s\n' "$target"
  else
    rm -rf "$target"
    printf '[removed] %s\n' "$target"
  fi
}

while IFS= read -r -d '' path; do remove_target "$path"; done < <(find "$ROOT" \( -path "$ROOT/.git" -o -path "$ROOT/.venv" -o -path "$ROOT/venv" \) -prune -o -type d \( -name .next -o -name node_modules -o -name .turbo -o -name .cache -o -name playwright-report -o -name test-results -o -name coverage -o -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache -o -name .notes -o -name .tmp \) -print0)
while IFS= read -r -d '' path; do remove_target "$path"; done < <(find "$ROOT" \( -path "$ROOT/.git" -o -path "$ROOT/.venv" -o -path "$ROOT/venv" \) -prune -o -type f \( -name '*.log' -o -name '*.tmp' -o -name '*.temp' -o -name '*.bak' -o -name '*.backup' -o -name '*.old' -o -name '*.orig' -o -name '*.rej' -o -name '*.swp' -o -name '*.swo' -o -name 'tsconfig.tsbuildinfo' -o -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.sqlite3-shm' -o -name '*.sqlite3-wal' -o -name '.env' -o -name '.env.local' -o -name '*.pyc' -o -name '*~' \) -print0)
