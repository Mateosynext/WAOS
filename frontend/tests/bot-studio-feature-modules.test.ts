import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function lineCount(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8").split(/\r?\n/).length;
}

test("bot studio flow client stays thin and delegates to feature modules", () => {
  const client = fs.readFileSync(path.join(root, "app/bot-studio/BotStudioFlowClient.tsx"), "utf8");
  assert.ok(client.includes("useBotStudioFlowController"));
  assert.ok(client.includes("BotStudioFlowBody"));
  assert.ok(lineCount("app/bot-studio/BotStudioFlowClient.tsx") <= 140);
});

test("bot studio flow logic is split into dedicated feature modules", () => {
  const expected = [
    "features/bot-studio/flow/types.ts",
    "features/bot-studio/flow/BotStudioFlowBody.tsx",
    "features/bot-studio/flow/useBotStudioFlowController.ts",
    "features/bot-studio/flow/flowActionDeps.ts",
    "features/bot-studio/flow/useBotStudioFlowActionHelpers.ts",
    "features/bot-studio/flow/useBotStudioFlowActions.ts",
    "features/bot-studio/flow/useBotStudioCreateFlowActions.ts",
    "features/bot-studio/flow/useBotStudioReconfigureFlowActions.ts",
    "features/bot-studio/flow/useBotStudioFlowNavigation.ts",
    "features/bot-studio/flow/useBotStudioFlowStateModel.ts",
    "features/bot-studio/flow/useBotStudioFlowTelemetry.ts",
    "features/bot-studio/api/wizardEndpoints.ts",
  ];
  for (const relativePath of expected) {
    assert.ok(fs.existsSync(path.join(root, relativePath)), relativePath);
  }
  assert.ok(lineCount("features/bot-studio/flow/BotStudioFlowBody.tsx") <= 120);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowController.ts") <= 140);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowActions.ts") <= 120);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioCreateFlowActions.ts") <= 160);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioReconfigureFlowActions.ts") <= 120);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowActionHelpers.ts") <= 180);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowNavigation.ts") <= 140);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowStateModel.ts") <= 220);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowTelemetry.ts") <= 80);
});
