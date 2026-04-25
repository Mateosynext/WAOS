import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(root, "..");

function readFrontend(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function readRepo(relativePath: string) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

test("AI Autopilot accept-all respects the backend max_autofix_rounds contract", () => {
  const screenModels = readFrontend("features/bot-studio/flow/wizardScreenModels.ts");
  const browserApi = readFrontend("features/bot-studio/services/wizardApi.ts");
  const proxyRoute = readFrontend("app/api/onboarding/wizard/ai-autopilot/route.ts");
  const serverData = readFrontend("app/lib/data/wizard.ts");

  assert.doesNotMatch(screenModels, /maxAutofixRounds:\s*3/);
  assert.match(screenModels, /maxAutofixRounds:\s*2/);
  assert.match(browserApi, /max_autofix_rounds:\s*clampAutofixRounds\(request\.maxAutofixRounds\)/);
  assert.match(proxyRoute, /normalizeWizardAiAutopilotProxyPayload\(await readWizardJsonBody\(request\)\)/);
  assert.match(serverData, /max_autofix_rounds:\s*clampAutofixRounds\(request\.maxAutofixRounds\)/);
});

test("AI Autopilot does not coerce string false into auto_apply true", () => {
  const proxyRoute = readFrontend("app/api/onboarding/wizard/ai-autopilot/route.ts");
  const browserApi = readFrontend("features/bot-studio/services/wizardApi.ts");
  const serverData = readFrontend("app/lib/data/wizard.ts");

  const contract = readFrontend("features/bot-studio/services/wizardAutopilotContract.ts");
  assert.match(contract, /export function parseAutopilotBoolean\(value: unknown\)/);
  assert.match(contract, /value\.trim\(\)\.toLowerCase\(\) === "true"/);
  assert.match(browserApi, /auto_apply:\s*request\.autoApply === true/);
  assert.match(serverData, /auto_apply:\s*request\.autoApply === true/);
  assert.doesNotMatch(proxyRoute, /\bBoolean\(body\?\.auto_apply/);
});

test("AI Autopilot surfaces backend validation details instead of a generic validation failed", () => {
  const routeHelpers = readFrontend("app/api/onboarding/wizard/route-helpers.ts");
  const browserApi = readFrontend("features/bot-studio/services/wizardApi.ts");

  assert.match(routeHelpers, /function resolveWizardDetails/);
  assert.match(routeHelpers, /details:\s*details \|\| undefined/);
  assert.match(browserApi, /function extractWizardErrorMessage/);
  assert.match(browserApi, /first\.loc/);
  assert.match(browserApi, /first\.msg/);
});

test("AI Autopilot keeps dry-run wizard freshness and navigates with wizard_id", () => {
  const screenModels = readFrontend("features/bot-studio/flow/wizardScreenModels.ts");
  const assistant = readFrontend("features/bot-studio/create/AiSetupAssistant.tsx");
  const backend = readRepo("backend/app/vertical_onboarding_ai_prefill.py");

  assert.match(screenModels, /const nextWizard = asRecord\(dryRunResult\.wizard \|\| result\.wizard\)/);
  assert.match(screenModels, /setValidatedWizardRevision\(validatedRevision\)/);
  assert.match(assistant, /function buildValidateHref/);
  assert.match(assistant, /\?wizard_id=\$\{encodeURIComponent\(wizardId\)\}/);
  assert.match(assistant, /router\.push\(buildValidateHref\(wired\)\)/);
  assert.match(backend, /wizard = _as_record\(dry_run\.get\("wizard"\)\) or wizard/);
});


test("AI Autopilot production hardening rejects malformed proxy inputs before backend side effects", () => {
  const routeHelpers = readFrontend("app/api/onboarding/wizard/route-helpers.ts");
  const autopilotRoute = readFrontend("app/api/onboarding/wizard/ai-autopilot/route.ts");
  const prefillRoute = readFrontend("app/api/onboarding/wizard/ai-prefill/route.ts");
  const assistant = readFrontend("features/bot-studio/create/AiSetupAssistant.tsx");
  const contract = readFrontend("features/bot-studio/services/wizardAutopilotContract.ts");
  const schemas = readRepo("backend/app/schemas/onboarding.py");

  assert.match(contract, /AUTOPILOT_MAX_AUTOFIX_ROUNDS = 2/);
  assert.match(contract, /export function parseAutopilotBoolean\(value: unknown\)/);
  assert.match(routeHelpers, /export async function readWizardJsonBody/);
  assert.match(routeHelpers, /json_invalid/);
  assert.match(routeHelpers, /X-Content-Type-Options/);
  assert.match(autopilotRoute, /normalizeWizardAiAutopilotProxyPayload\(await readWizardJsonBody\(request\)\)/);
  assert.match(autopilotRoute, /hasRequiredAutopilotScope/);
  assert.match(prefillRoute, /hasRequiredAutopilotScope/);
  assert.match(assistant, /maxLength=\{AI_DESCRIPTION_MAX_LENGTH\}/);
  assert.match(assistant, /normalizeAiDescription\(event\.currentTarget\.value\)/);
  assert.match(schemas, /GuidedOnboardingAiAutopilotRequest\(BaseModel\):/);
  assert.match(schemas, /model_config = ConfigDict\(extra="forbid", str_strip_whitespace=True\)/);
  assert.match(schemas, /organization_id: str = Field\(min_length=1, max_length=120\)/);
});
