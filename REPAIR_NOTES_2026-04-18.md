# WAOS repair notes — 2026-04-18

## Fixes applied

1. Agent policy budget evaluation
- Made budget windows deterministic in test/replay contexts by anchoring the evaluation clock to the latest conversation or tool-run evidence instead of the wall clock only.
- Prevents false negatives in specialist-policy budget blocking when evaluating historical fixtures.

2. Test import path consistency
- Hardened `backend/tests/conftest.py` to expose both repository root and backend root on `sys.path`.
- Fixes mixed `backend.app...` and `app...` imports when collecting grouped test subsets.

3. Commerce payment cleanup integrity
- Added migration `2026-04-18-phase28-payment-delete-cleanup-v1`.
- Introduces a SQLite cleanup trigger that deletes outcome facts/events/exposures linked to a payment before deleting `commerce_payments` rows.
- Prevents foreign-key failures when replacing payment fixtures in replay/proactive tests.

4. Release/source hygiene
- Removed generated PDFs from `backend/app/artifacts/reports/`, preserving only `.gitkeep`.
- Hardened release exclusions and release gate checks to also block `*.sqlite3-shm` and `*.sqlite3-wal` files.

## Validation performed
- Python compilation: `python -m compileall backend/app backend/worker.py`
- Targeted runtime and orchestration suite: 13 passed
- Additional high-value suite: 17 passed

Total validated tests in this repair pass: 30 passed.
