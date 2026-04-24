import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const frontendRoot = process.cwd();

function read(relativePath: string) {
  return fs.readFileSync(path.join(frontendRoot, relativePath), "utf8");
}

test("legacy global barrels and Bot Studio shims stay deleted", () => {
  for (const legacyPath of [
    "app/actions.ts",
    "app/components.tsx",
    "app/lib/waos.ts",
    "app/lib/contracts.ts",
    "app/bot-studio/useBotStudioWizardState.ts",
    "app/bot-studio/createScreens.tsx",
    "app/bot-studio/wizardReviewSections.tsx",
  ]) {
    assert.equal(fs.existsSync(path.join(frontendRoot, legacyPath)), false, legacyPath);
  }
});

test("eslint blocks legacy Bot Studio shims and global barrels", () => {
  const eslint = read(".eslintrc.json");
  const config = JSON.parse(eslint);
  const rule = config.rules["no-restricted-imports"];
  assert.equal(rule[0], "error");
  const patterns = rule[1].patterns;
  for (const forbidden of [
    "@/app/lib/waos",
    "@/app/lib/contracts",
    "@/app/components",
    "@/app/actions",
    "@/app/bot-studio/*",
    "../components",
    "../actions",
    "../lib/waos",
    "../lib/contracts",
  ]) {
    assert.equal(patterns.includes(forbidden), true, forbidden);
  }
});

test("wizard route response preserves transport metadata", () => {
  const helper = read("app/api/onboarding/wizard/route-helpers.ts");
  assert.match(helper, /X-Request-Id/);
  assert.match(helper, /X-Correlation-Id/);
  assert.match(helper, /X-Error-Code/);
  assert.match(helper, /error_type/);
  assert.match(helper, /request_id/);
  assert.match(helper, /correlation_id/);
  assert.match(helper, /status,/);
});
