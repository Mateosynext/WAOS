# Domains, platform/hygiene, and legacy cleanup

## What changed
- Moved the catalog v9 DDL out of `backend/app/domains/*` into `backend/db/migrations/015_catalog_v9.sql`.
- Reduced `backend/app/domains/schema_setup.py` to a compatibility wrapper over migration SQL.
- Removed duplicated raw DB helpers and audit inserts from domain modules that still carried infra concerns (`catalog.py`, `bot_behavior.py`, `customer_experience.py`).
- Moved observability implementation under `backend/app/platform/observability.py` and kept `backend/app/observability.py` as a thin compatibility facade.
- Tightened repo hygiene to flag local sqlite/db artifacts the same way release validation already did.
- Removed committed local runtime artifacts (`backend/.waos-local.db`, `frontend/tsconfig.tsbuildinfo`).
- Strengthened architecture coverage so historical root shims cannot silently come back.

## Intent
This pass does not make `domains/` fully pure yet, but it removes the two biggest impurities called out in review: duplicated catalog DDL inside the domain package and repeated inline infra helpers.
