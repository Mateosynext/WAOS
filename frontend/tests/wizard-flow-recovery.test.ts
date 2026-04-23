import test from "node:test";
import assert from "node:assert/strict";

import { getWizardRouteRecovery, mapRouteStepToWizardUiStep, mapWizardUiStepToRouteStep } from "../app/bot-studio/wizardFlowRecovery";
import type { WizardInstance } from "../app/bot-studio/wizard-types";

test("route/ui mappings keep create and reconfigure flows aligned", () => {
  assert.equal(mapRouteStepToWizardUiStep("create", "validate"), "dry_run");
  assert.equal(mapRouteStepToWizardUiStep("reconfigure", "dry-run"), "dry_run");
  assert.equal(mapWizardUiStepToRouteStep("create", "confirm"), "apply");
  assert.equal(mapWizardUiStepToRouteStep("reconfigure", "review", true), "diff");
  assert.equal(mapWizardUiStepToRouteStep("reconfigure", "review", false), "select");
});

test("reconfigure recovery falls back to diff when confirm lost its dry run", () => {
  const wizard: WizardInstance = {
    id: "wiz_1",
    organization_id: "org_1",
    status: "draft",
    current_step: "launch_review",
  };

  const recovery = getWizardRouteRecovery({
    mode: "reconfigure",
    routeStep: "confirm",
    wizard,
    hasDryRunResult: false,
    hasSelectedBot: true,
  });

  assert.ok(recovery);
  assert.equal(recovery?.routeStep, "diff");
  assert.equal(recovery?.reason, "missing_dry_run");
});

test("create recovery falls back to the persisted route when success is opened without apply", () => {
  const wizard: WizardInstance = {
    id: "wiz_2",
    organization_id: "org_1",
    status: "draft",
    current_step: "catalog_offer",
  };

  const recovery = getWizardRouteRecovery({
    mode: "create",
    routeStep: "success",
    wizard,
    hasDryRunResult: false,
  });

  assert.ok(recovery);
  assert.equal(recovery?.routeStep, "offer");
  assert.equal(recovery?.reason, "missing_apply");
});
