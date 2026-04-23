# Frontend vertical fallback and tooling refactor

## Done
- Replaced the monolithic `frontend/app/lib/vertical-fallback.ts` blob with a modular dataset under `frontend/app/lib/vertical-fallback/`.
- Added `index.json` as the versioned catalog index and `profiles/*.json` per vertical.
- Added an indexed loader in `frontend/app/lib/vertical-fallback/index.ts` with per-vertical loading, cache, and contract normalization.
- Updated `frontend/app/lib/data/verticals.ts` to await the fallback loader.
- Added repo-policy checks for forbidden artifacts, broken markdown doc references, and leaked legacy root shims.
- Wired the shared policy into `scripts/check_repo_hygiene.py`, `scripts/release_gate.py`, and `scripts/release_build.py`.
- Restored the missing docs referenced from `README.md`.

## Remaining follow-up
- Move the fallback dataset generation closer to backend/catalog publishing so the frontend copy is generated instead of hand-maintained.
- Add a small build-time validator that checks duplicate subvertical ids and duplicate aliases across vertical files.
- Consider exposing the fallback catalog to tests through a dedicated fixture helper once the frontend test environment has dependencies available again.
