#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

echo "[waos-worker] running release-candidate validation"
python scripts/validate_release_candidate.py

if [[ "${WAOS_SKIP_PREFLIGHT:-false}" != "true" ]]; then
  echo "[waos-worker] running production preflight"
  python scripts/preflight_check.py
fi

echo "[waos-worker] starting worker"
exec python worker.py
