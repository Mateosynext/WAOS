import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function lineCount(relativePath: string) {
  return read(relativePath).split(/\r?\n/).length;
}

test("bot studio route stays thin and delegates to feature modules", () => {
  const route = read("features/bot-studio/BotStudioRoute.tsx");
  assert.ok(route.includes("useBotStudioFlowController"));
  assert.ok(route.includes("BotStudioFlowBody"));
  assert.ok(lineCount("features/bot-studio/BotStudioRoute.tsx") <= 160);
});

test("bot studio flow logic is split into dedicated feature modules", () => {
  const expected = [
    "features/bot-studio/BotStudioRoute.tsx",
    "features/bot-studio/domain/wizardTypes.ts",
    "features/bot-studio/domain/flowConfig.ts",
    "features/bot-studio/domain/wizardProgressGuards.ts",
    "features/bot-studio/domain/wizardStepFlow.ts",
    "features/bot-studio/domain/navigationState.ts",
    "features/bot-studio/domain/wizardEnterpriseGuards.ts",
    "features/bot-studio/domain/wizardFlowRecovery.ts",
    "features/bot-studio/services/wizardApi.ts",
    "features/bot-studio/services/wizardPayloadBuilders.ts",
    "features/bot-studio/services/wizardReactiveData.ts",
    "features/bot-studio/server/loadBotStudioRoute.ts",
    "features/bot-studio/ui/flowUi.tsx",
    "features/bot-studio/ui/VerticalPicker.tsx",
    "features/bot-studio/ui/SubverticalPicker.tsx",
    "features/bot-studio/reconfigure/reconfigureScreens.tsx",
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
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowStateModel.ts") <= 430);
  assert.ok(lineCount("features/bot-studio/flow/useBotStudioFlowTelemetry.ts") <= 80);
});

test("bot studio feature modules do not import app bot-studio internals", () => {
  const featureFiles = expectedFeatureFiles(root);
  for (const filePath of featureFiles) {
    const source = fs.readFileSync(filePath, "utf8");
    assert.doesNotMatch(source, /app\/bot-studio/);
  }
});

function expectedFeatureFiles(directory: string): string[] {
  const start = path.join(directory, "features/bot-studio");
  const pending = [start];
  const files: string[] = [];
  while (pending.length) {
    const current = pending.pop()!;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(absolute);
      if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) files.push(absolute);
    }
  }
  return files;
}
