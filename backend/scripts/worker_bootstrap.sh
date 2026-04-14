#!/usr/bin/env bash
set -euo pipefail
export RUN_BOOTSTRAP_SEED=${RUN_BOOTSTRAP_SEED:-false}
python scripts/preflight_check.py
exec python worker.py
