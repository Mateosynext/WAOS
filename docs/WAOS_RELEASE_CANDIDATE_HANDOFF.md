# WAOS release candidate handoff

## Canonical handoff files
- Root summary: `RELEASE_HANDOFF.md`
- Final release notes: `RELEASE_FINAL.md`
- Validation snapshot: `VALIDATION_REPORT.md`

## Packaging expectations
- `scripts/check_repo_hygiene.py` must pass before packaging.
- `scripts/release_gate.py . --profile source` must pass on the source tree.
- `scripts/release_build.py` now aborts if the source tree still contains forbidden artifacts, broken doc references, or leaked legacy root shims.

## Source-tree guarantees
- No local SQLite databases.
- No `*.tsbuildinfo` artifacts.
- No Python bytecode or `__pycache__` in distributable source.
- No broken `docs/*.md` references from README or other markdown files.

## Current architectural handoff themes
- Backend application layer is split by use case with presenter/policy extraction.
- AI runtime lives behind `backend/app/ai_runtime/` and root modules act as façades.
- Frontend app shell and Bot Studio are split into thinner route shims plus feature modules.
- Vertical fallback data is modularized under `frontend/app/lib/vertical-fallback/`.
