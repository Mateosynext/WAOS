import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function exists(relativePath: string) {
  return fs.existsSync(path.join(root, relativePath));
}

test("bot studio flow body lazy loads step screens", () => {
  const body = read("features/bot-studio/flow/BotStudioFlowBody.tsx");
  assert.match(body, /import dynamic from "next\/dynamic"/);
  assert.match(body, /import\("\.\.\/context\/screens\/CreateReviewScreen"\)/);
  assert.match(body, /import\("\.\.\/context\/screens\/CreateValidateScreen"\)/);
  assert.match(body, /import\("\.\.\/context\/screens\/CreateApplyScreen"\)/);
  assert.match(body, /import\("\.\.\/reconfigure\/screens\/ReconfigureDryRunScreen"\)/);
  assert.doesNotMatch(body, /from "\.\.\/context\/createScreens"/);
  assert.doesNotMatch(body, /from "@\/features\/bot-studio\/reconfigure\/reconfigureScreens"/);
});

test("review bundle is split into concrete components", () => {
  for (const relativePath of [
    "features/bot-studio/review/ValidationSnapshotPanel.tsx",
    "features/bot-studio/review/VerticalScorecardPanel.tsx",
    "features/bot-studio/review/DiffCard.tsx",
    "features/bot-studio/review/StickySummaryRail.tsx",
    "features/bot-studio/review/PackPreviewBlock.tsx",
    "features/bot-studio/review/WizardReviewSummary.tsx",
  ]) {
    assert.ok(exists(relativePath), relativePath);
  }
  assert.ok(read("features/bot-studio/review/wizardReviewSections.tsx").split(/\r?\n/).length <= 20);
});

test("heavy app routes expose skeleton loading states", () => {
  for (const relativePath of [
    "app/inbox/loading.tsx",
    "app/integrations/loading.tsx",
    "app/verticals/loading.tsx",
    "app/bot-studio/loading.tsx",
  ]) {
    const source = read(relativePath);
    assert.match(source, /animate-pulse/);
    assert.doesNotMatch(source, /spinner/i);
  }
});

test("integrations page only loads active heavy section data", () => {
  const page = read("app/integrations/page.tsx");
  const model = read("features/integrations/server/getIntegrationsPageModel.ts");
  assert.match(page, /getIntegrationsPageModel/);
  assert.match(model, /normalizeIntegrationSection/);
  assert.match(model, /section === "sync"[\s\S]*getIntegrationSyncRuns\(\)/);
  assert.match(model, /section === "sync"[\s\S]*getPayments\(\)/);
  assert.match(model, /section === "observabilidad"[\s\S]*getIntegrationObservability\(\)/);
  assert.match(model, /section === "observabilidad"[\s\S]*getIntegrationEvents\(\)/);
  assert.match(model, /section === "riesgo"[\s\S]*getIntegrationCenter\(\)/);
  assert.match(model, /section === "configuracion"[\s\S]*getGoogleCalendars/);
  assert.doesNotMatch(model, /Promise\.all\(\[\s*getBots\(\),\s*getIntegrations\(\),\s*getIntegrationSyncRuns\(\),\s*getIntegrationObservability\(\),\s*getIntegrationEvents\(\),\s*getPayments\(\),\s*getIntegrationCenter\(\),\s*\]\)/);
});
