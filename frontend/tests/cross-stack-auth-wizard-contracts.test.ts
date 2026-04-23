import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(frontendRoot, "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(frontendRoot, relativePath), "utf8");
}

function loadOpenApi() {
  const result = spawnSync("python", ["-c", `from backend.app.main import app; import json; print(json.dumps(app.openapi()))`], {
    cwd: repoRoot,
    env: { ...process.env, PYTHONPATH: repoRoot },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr || "OpenAPI export should succeed");
  return JSON.parse(result.stdout);
}

test("frontend auth helpers and backend auth routes stay aligned", () => {
  const openapi = loadOpenApi();
  const sharedSession = read("app/lib/auth/shared-session.ts");

  assert.match(sharedSession, /AUTH_ME_PATH = "\/api\/v1\/auth\/me"/);
  assert.match(sharedSession, /AUTH_REFRESH_PATH = "\/api\/v1\/auth\/refresh"/);
  assert.ok(openapi.paths?.["/api/v1/auth/me"]?.get);
  assert.ok(openapi.paths?.["/api/v1/auth/refresh"]?.post);
});

test("frontend wizard path builders and backend onboarding routes stay aligned", () => {
  const openapi = loadOpenApi();
  const wizardEndpoints = read("app/lib/data/wizardEndpoints.ts");

  assert.match(wizardEndpoints, /WIZARD_API_PREFIX = "\/api\/v1\/onboarding\/wizard"/);
  assert.match(wizardEndpoints, /buildWizardBackendBasePath/);
  assert.match(wizardEndpoints, /buildWizardStepBackendPath/);
  assert.match(wizardEndpoints, /buildWizardDryRunBackendPath/);
  assert.match(wizardEndpoints, /buildWizardApplyBackendPath/);
  assert.match(wizardEndpoints, /buildWizardBlueprintBackendPath/);

  for (const route of [
    "/api/v1/onboarding/wizard/blueprint",
    "/api/v1/onboarding/wizard/start",
    "/api/v1/onboarding/wizard/{wizard_id}",
    "/api/v1/onboarding/wizard/{wizard_id}/steps/{step_key}",
    "/api/v1/onboarding/wizard/{wizard_id}/dry-run",
    "/api/v1/onboarding/wizard/{wizard_id}/apply",
  ]) {
    assert.ok(openapi.paths?.[route], `${route} should exist in backend OpenAPI`);
  }
});
