import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "..");

test("critical login, release and e2e surfaces exist", () => {
  const files = [
    "app/components/LoginForm.tsx",
    "app/releases/page.tsx",
    "app/insights/page.tsx",
    "app/api/auth/sso/start/route.ts",
    "playwright.config.ts",
    "playwright.mocked.config.ts",
    "playwright.real.config.ts",
    "tests/e2e/login-mfa.mock.spec.ts",
    "tests/e2e/portal-agenda-multiorg.mock.spec.ts",
    "tests/e2e/reports.mock.spec.ts",
    "tests/e2e/auth-mfa-refresh.real.spec.ts",
    "tests/e2e/agenda-payments-multiorg.real.spec.ts",
    "tests/e2e/reports-release.real.spec.ts",
  ];
  for (const file of files) assert.equal(fs.existsSync(path.join(root, file)), true, `${file} should exist`);
});
