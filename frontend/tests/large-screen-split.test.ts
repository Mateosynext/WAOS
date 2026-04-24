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

test("large app pages are thin wrappers over feature modules", () => {
  for (const route of ["inbox", "integrations", "verticals"]) {
    const source = read(`app/${route}/page.tsx`);
    assert.ok(source.split(/\r?\n/).length <= 12, `${route} page should stay thin`);
    assert.match(source, new RegExp(`features/${route === "verticals" ? "vertical-selection" : route}`));
  }
});

test("inbox owns fetching, shell, filters, list, detail and metrics in feature folders", () => {
  for (const relativePath of [
    "features/inbox/server/getInboxPageModel.ts",
    "features/inbox/components/InboxShell.tsx",
    "features/inbox/components/InboxFilters.tsx",
    "features/inbox/components/ConversationList.tsx",
    "features/inbox/components/ConversationDetail.tsx",
    "features/inbox/components/InboxMetrics.tsx",
    "features/inbox/actions/index.ts",
  ]) {
    assert.ok(exists(relativePath), relativePath);
  }
  assert.match(read("features/inbox/server/getInboxPageModel.ts"), /getConversations/);
  assert.match(read("features/inbox/components/InboxShell.tsx"), /ConversationList/);
});

test("integrations page is split by active section with colocated loaders", () => {
  for (const relativePath of [
    "features/integrations/server/getIntegrationsPageModel.ts",
    "features/integrations/configuration/ConfigurationSection.tsx",
    "features/integrations/configuration/SectionLoader.tsx",
    "features/integrations/observability/ObservabilitySection.tsx",
    "features/integrations/observability/SectionLoader.tsx",
    "features/integrations/events/SectionLoader.tsx",
    "features/integrations/payments/SectionLoader.tsx",
    "features/integrations/risk/RiskSection.tsx",
    "features/integrations/risk/SectionLoader.tsx",
    "features/integrations/sync/SyncSection.tsx",
    "features/integrations/sync/StatusSection.tsx",
    "features/integrations/sync/SectionLoader.tsx",
  ]) {
    assert.ok(exists(relativePath), relativePath);
  }
  assert.match(read("features/integrations/components/IntegrationsShell.tsx"), /ConfigurationSection/);
  assert.match(read("features/integrations/components/IntegrationsShell.tsx"), /ObservabilitySection/);
});

test("vertical selection is split into catalog, profile, readiness and transactional panels", () => {
  for (const relativePath of [
    "features/vertical-selection/server/getVerticalsPageModel.ts",
    "features/vertical-selection/components/VerticalCatalog.tsx",
    "features/vertical-selection/components/VerticalProfile.tsx",
    "features/vertical-selection/components/SubverticalPanel.tsx",
    "features/vertical-selection/components/VerticalReadiness.tsx",
    "features/vertical-selection/components/TransactionalMotorPanel.tsx",
  ]) {
    assert.ok(exists(relativePath), relativePath);
  }
  assert.match(read("features/vertical-selection/components/VerticalsShell.tsx"), /TransactionalMotorPanel/);
});
