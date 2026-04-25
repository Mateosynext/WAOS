#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"
python backend/scripts/deploy_guard.py
python -m unittest discover -s backend/tests -v
python backend/scripts/smoke_test.py
