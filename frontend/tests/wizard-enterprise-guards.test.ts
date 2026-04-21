import test from "node:test";
import assert from "node:assert/strict";
import {
  deriveWizardConsistencyRecovery,
  fingerprintWizardValue,
  readWizardAutosaveMetrics,
  readWizardTimelineEvents,
  recordWizardAutosaveMetric,
  recordWizardTimelineEvent,
} from "../app/bot-studio/wizardEnterpriseGuards";

class MemoryStorage {
  private store = new Map<string, string>();
  getItem(key: string) {
    return this.store.has(key) ? this.store.get(key)! : null;
  }
  setItem(key: string, value: string) {
    this.store.set(key, value);
  }
}

const context = {
  mode: "create" as const,
  organizationId: "org_1",
  botId: "bot_1",
  wizardId: "wiz_1",
  verticalId: "dental",
  subvertical: "ortodoncia",
};

test("wizard enterprise telemetry keeps a capped timeline", () => {
  const storage = new MemoryStorage();
  for (let index = 0; index < 140; index += 1) {
    recordWizardTimelineEvent(storage, context, { type: `event_${index}` });
  }
  const events = readWizardTimelineEvents(storage, context);
  assert.equal(events.length, 120);
  assert.equal(events[0]?.type, "event_20");
  assert.equal(events.at(-1)?.type, "event_139");
});

test("wizard enterprise telemetry aggregates autosave metrics", () => {
  const storage = new MemoryStorage();
  recordWizardAutosaveMetric(storage, context, { result: "success", durationMs: 1200, stepCount: 2 });
  recordWizardAutosaveMetric(storage, context, { result: "error", durationMs: 300, stepCount: 1 });
  recordWizardAutosaveMetric(storage, context, { result: "ignored", durationMs: 0, stepCount: 0 });
  const metrics = readWizardAutosaveMetrics(storage, context);
  assert.equal(metrics.attempts, 3);
  assert.equal(metrics.successes, 1);
  assert.equal(metrics.errors, 1);
  assert.equal(metrics.ignored, 1);
  assert.equal(metrics.maxDurationMs, 1200);
  assert.equal(metrics.lastStepCount, 0);
  assert.equal(metrics.averageDurationMs, 500);
});

test("wizard enterprise auto recovery clamps impossible create steps", () => {
  const recovery = deriveWizardConsistencyRecovery({
    mode: "create",
    activeStep: "integrations",
    persistedStep: "basics",
    clientAllowedStep: "knowledge",
    hasAppliedWizard: false,
  });
  assert.equal(recovery?.step, "basics");
  assert.equal(recovery?.reason, "ahead_of_persisted_progress");
});

test("wizard enterprise auto recovery sends reconfigure flow back to review when dry run vanished", () => {
  const recovery = deriveWizardConsistencyRecovery({
    mode: "reconfigure",
    activeStep: "confirm",
    persistedStep: "review",
    hasDryRunResult: false,
    hasAppliedWizard: false,
  });
  assert.equal(recovery?.step, "review");
  assert.equal(recovery?.reason, "missing_dry_run");
});


test("wizard enterprise fingerprint stays stable across object key order", () => {
  const left = fingerprintWizardValue({ b: 2, a: { y: ["x"], x: 1 } });
  const right = fingerprintWizardValue({ a: { x: 1, y: ["x"] }, b: 2 });
  assert.equal(left, right);
});
