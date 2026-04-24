import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("bot studio wizard state exposes domain slices and actions", () => {
  const source = read("features/bot-studio/context/useBotStudioWizardState.ts");
  for (const expected of [
    "export type WizardScopeState",
    "export type WizardBasicsState",
    "export type WizardCatalogState",
    "export type WizardKnowledgeState",
    "export type WizardIntegrationsState",
    "export function useWizardScope",
    "export function useWizardBasics",
    "export function useWizardCatalog",
    "export function useWizardKnowledge",
    "export function useWizardIntegrations",
    "export function useWizardAutosave",
  ]) {
    assert.match(source, new RegExp(expected));
  }
});

test("bot studio screens receive view models instead of the full wizard state", () => {
  const body = read("features/bot-studio/flow/BotStudioFlowBody.tsx");
  const screens = read("features/bot-studio/context/screens/CreateContextScreen.tsx");
  const stateModel = read("features/bot-studio/flow/useBotStudioFlowStateModel.ts");

  assert.match(body, /viewModel=\{createScreens\.context\.viewModel\}/);
  assert.match(body, /actions=\{createScreens\.context\.actions\}/);
  assert.doesNotMatch(body, /handlers=/);
  assert.doesNotMatch(body, /createState=/);
  assert.match(screens, /CreateContextScreen\(\{ viewModel: state, actions: handlers \}/);
  assert.match(stateModel, /CreateWizardScreenModels/);
  assert.match(stateModel, /ReconfigureWizardScreenModels/);
});

test("wizard payload memo uses explicit dependencies instead of the whole state object", () => {
  const source = read("features/bot-studio/flow/useBotStudioFlowStateModel.ts");
  assert.doesNotMatch(source, /buildWizardPayloads[\s\S]*\], \[props\.routeMode, selectedOrganization, state\]\)/);
  assert.doesNotMatch(source, /\[state\]/);
  assert.match(source, /basics\.businessName/);
  assert.match(source, /catalog\.servicesText/);
  assert.match(source, /integrations\.selectedIntegrationKeys/);
});


test("wizard initial selected vertical falls back to route params before persisted answers exist", () => {
  const source = read("features/bot-studio/context/useBotStudioWizardState.ts");

  assert.match(source, /selectedVerticalId:\s*initialConfirmedVerticalId\s*\|\|\s*initialVerticalId/);
  assert.match(source, /selectedSubvertical:\s*initialConfirmedSubvertical\s*\|\|\s*initialSubvertical/);
  assert.match(source, /candidateVerticalId:\s*initialCandidateVerticalId/);
  assert.match(source, /candidateSubvertical:\s*initialCandidateSubvertical/);
});
