import test from "node:test";
import assert from "node:assert/strict";
import { getCreateAutosaveStepKeys, resolveWizardInitialStep } from "../app/bot-studio/wizardStepFlow";

test("wizard step resolution stays aligned between hydration and client flow", () => {
  assert.equal(resolveWizardInitialStep("create", { current_step: "business_basics" } as never), "basics");
  assert.equal(resolveWizardInitialStep("create", { current_step: "catalog_offer" } as never), "offer");
  assert.equal(resolveWizardInitialStep("create", { current_step: "knowledge_seed" } as never), "knowledge");
  assert.equal(resolveWizardInitialStep("create", { current_step: "integrations_rules" } as never), "integrations");
  assert.equal(resolveWizardInitialStep("create", { current_step: "launch_review" } as never), "review");
  assert.equal(resolveWizardInitialStep("reconfigure", null), "review");
  assert.equal(resolveWizardInitialStep("create", { status: "applied" } as never), "publish");
  assert.equal(resolveWizardInitialStep("create", null, "simulate"), "simulate");
});

test("wizard step override never jumps ahead of persisted create progress", () => {
  assert.equal(resolveWizardInitialStep("create", { current_step: "business_basics" } as never, "integrations"), "basics");
  assert.equal(resolveWizardInitialStep("create", { current_step: "catalog_offer" } as never, "review"), "offer");
  assert.equal(resolveWizardInitialStep("create", { current_step: "knowledge_seed" } as never, "scope"), "scope");
});

test("create autosave never persists future steps before the user reaches them", () => {
  assert.deepEqual(getCreateAutosaveStepKeys("scope"), ["vertical_fit"]);
  assert.deepEqual(getCreateAutosaveStepKeys("basics"), ["vertical_fit", "business_basics"]);
  assert.deepEqual(getCreateAutosaveStepKeys("offer"), ["vertical_fit", "business_basics", "catalog_offer"]);
  assert.deepEqual(getCreateAutosaveStepKeys("knowledge"), ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed"]);
  assert.deepEqual(getCreateAutosaveStepKeys("integrations"), ["vertical_fit", "business_basics", "catalog_offer", "knowledge_seed", "integrations_rules"]);
});
