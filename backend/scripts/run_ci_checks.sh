#!/usr/bin/env bash
set -euo pipefail
python -m unittest discover -s backend/tests -v
python backend/scripts/smoke_test.py
