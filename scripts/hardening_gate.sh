#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf '[1/3] repo hygiene\n'
python3 "$ROOT/scripts/check_repo_hygiene.py"

printf '[2/3] frontend typecheck\n'
(cd "$ROOT/frontend" && npm run typecheck)

printf '[3/3] hardening summary\n'
printf 'OK: repo sin archivos basura detectados y frontend con typecheck verde.\n'
printf 'Nota: el build completo puede requerir variables de entorno y recursos fuera del sandbox.\n'
