# P1.7 Frontend certification requirement

Status: local packaging validation did not certify the full frontend npm path. This is not recorded as a definitive product-code failure, but it is a release-certification gap.

In this packaging environment, `npm --version` and npm-based commands did not complete reliably, so this package must not claim a clean local run for:

```bash
cd frontend
npm ci --no-audit --no-fund
npm audit --audit-level=moderate
npm run typecheck
npm run build
npm run test:node
```

Blocking release policy:

- A production tag/build must not be promoted unless the frontend npm gates above complete successfully in GitHub Actions or an equivalent reproducible CI environment.
- Local validation that cannot execute `npm` is insufficient evidence for frontend certification.
- Render backend deployment is not full-stack certification because Render is rooted at `backend`.
- `scripts/validate_release_in_ci.sh` is the authoritative ZIP validation path and now includes `npm run test:node` in addition to `npm ci`, `npm audit --audit-level=moderate`, `npm run typecheck`, and `npm run build`.

CI alignment:

- `.github/workflows/waos-release-validation.yml` runs the frontend install/SCA/typecheck/build path and now also runs `npm run test:node`.
- `scripts/validate_release_in_ci.sh` runs the same frontend certification gates during `production-certification-from-zip`.
- The frontend build remains required to produce `.next/BUILD_ID`; absence of that file fails certification.

Auditor note:

This package documents the failed local npm-certification attempt rather than masking it. The release can be considered frontend-certified only after CI records a clean run of the required npm gates.
