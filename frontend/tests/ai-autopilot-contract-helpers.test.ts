import test from "node:test";
import assert from "node:assert/strict";

import {
  AI_DESCRIPTION_MAX_LENGTH,
  AUTOPILOT_MAX_AUTOFIX_ROUNDS,
  clampAutofixRounds,
  normalizeAiDescription,
  normalizeWizardAiAutopilotProxyPayload,
  parseAutopilotBoolean,
} from "../features/bot-studio/services/wizardAutopilotContract";

test("Autopilot contract helpers clamp and parse unsafe values", () => {
  assert.equal(AUTOPILOT_MAX_AUTOFIX_ROUNDS, 2);
  assert.equal(clampAutofixRounds(999), 2);
  assert.equal(clampAutofixRounds(0), 1);
  assert.equal(clampAutofixRounds("abc"), 2);
  assert.equal(parseAutopilotBoolean("false"), false);
  assert.equal(parseAutopilotBoolean("true"), true);
  assert.equal(parseAutopilotBoolean(1), true);
  assert.equal(parseAutopilotBoolean(0), false);
});

test("Autopilot proxy payload normalization is bounded and snake/camel compatible", () => {
  const payload = normalizeWizardAiAutopilotProxyPayload({
    organizationId: " org_1 ",
    botId: " bot_1 ",
    maxAutofixRounds: 3,
    autoApply: "false",
    userDescription: "x".repeat(AI_DESCRIPTION_MAX_LENGTH + 100),
    existingAnswers: [],
  });

  assert.equal(payload.organizationId, "org_1");
  assert.equal(payload.botId, "bot_1");
  assert.equal(payload.maxAutofixRounds, 2);
  assert.equal(payload.autoApply, false);
  assert.equal(payload.userDescription.length, AI_DESCRIPTION_MAX_LENGTH);
  assert.deepEqual(payload.existingAnswers, {});
});

test("normalizeAiDescription always trims and bounds user text", () => {
  assert.equal(normalizeAiDescription(`  hola  `), "hola");
  assert.equal(normalizeAiDescription("x".repeat(AI_DESCRIPTION_MAX_LENGTH + 1)).length, AI_DESCRIPTION_MAX_LENGTH);
});
