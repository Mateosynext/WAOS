# P1.6 PostCSS audit release requirement

Status: PostCSS appears patched in source control, but production release certification is not complete until the frontend SCA gate runs cleanly.

Current package state:

- `frontend/package.json` pins `postcss` to `8.5.10`.
- `frontend/package.json` also overrides transitive `postcss` resolution to `8.5.10`.
- `frontend/package-lock.json` resolves the installed package at `node_modules/postcss` to `8.5.10`.
- The previously vulnerable nested `node_modules/next/node_modules/postcss` package entry is not present in the lockfile.

Required release validation:

```bash
cd frontend
npm audit --audit-level=moderate
```

This is a blocking production release requirement. A tag/build must not be promoted unless the moderate-level npm audit gate passes in CI or in the equivalent reproducible ZIP validation path.

CI alignment:

- `frontend/.npmrc` sets `audit-level=moderate`.
- `.github/workflows/waos-release-validation.yml` runs `npm audit --audit-level=moderate`.
- `scripts/validate_release_in_ci.sh` defaults `NPM_AUDIT_LEVEL` to `moderate` and runs `npm audit --audit-level="$NPM_AUDIT_LEVEL"`.

Local validation note:

- In this packaging environment, `npm audit --audit-level=moderate --package-lock-only` did not complete before the local timeout, likely because npm audit requires external registry access.
- Therefore this package records the requirement, but does not claim a local clean audit result.
- The authoritative certification signal remains the CI run of `npm audit --audit-level=moderate` during release validation.
