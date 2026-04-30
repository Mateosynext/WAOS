# WAOS P1.9 Hardened Release Notes — 2026-04-30

This patch reinforces the P1.8 release candidate so the source artifact fails closed instead of hanging or silently accepting weak packaging.

## Hardening added

- `backend/scripts/check_release_source_hardening.py`
  - Rejects generated/cache directories such as `node_modules`, `.next`, `__pycache__`, coverage and Playwright artifacts.
  - Rejects symlinks, special files, oversized files and secret-like suffixes such as `.pem`, `.key`, `.p12`, `.pfx`.
  - Verifies the CI gate still contains the required npm, SCA, pytest and live-AI certification steps.
  - Verifies the deterministic release gate still runs artifact integrity, source hardening, frontend guardrails and AI evals.

- `backend/scripts/release_gate.py`
  - Runs artifact integrity with an explicit timeout.
  - Runs the new source hardening check before backend/frontend guardrails.

- `scripts/validate_release_in_ci.sh`
  - Runs source hardening directly after repository hygiene.

- `scripts/validate_zip_reproducible.sh`
  - Replaces raw `unzip` with safe Python extraction.
  - Rejects path traversal, absolute paths, duplicate members, special files, symlinks, zip bombs and unexpectedly large ZIP members before extraction.

## Still required for production approval

Production promotion still requires a green CI run with:

```bash
bash scripts/validate_release_in_ci.sh
WAOS_REQUIRE_LIVE_AI_EVALS=1 WAOS_AI_EVAL_LIVE=1 OPENAI_API_KEY=... bash scripts/validate_release_in_ci.sh
```

The source artifact is now hardened to prevent incomplete or unsafe packages from reaching that certification step.
