# P1.2 PostCSS audit policy

Decision: do not accept the moderate PostCSS advisory as residual production risk.

Actions:
- Pin/override `postcss` to `8.5.10` at the frontend package level.
- Remove the vulnerable nested `next/node_modules/postcss@8.4.31` lockfile entry so installs resolve to the fixed top-level `postcss@8.5.10` under the explicit npm override.
- Raise frontend SCA gates from `audit-level=high` to `audit-level=moderate` in CI, `.npmrc`, and the release validation script.

Operational note: if a future Next.js release removes the exact `postcss@8.4.31` dependency, prefer upgrading Next and dropping the override after `npm audit --audit-level=moderate` remains clean.

P1.6 follow-up: `postcss@8.5.10` is pinned and overridden, but production release certification still requires a clean `npm audit --audit-level=moderate` run. See `POSTCSS_AUDIT_P1_6_2026-04-30.md`.
