import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceExtensions = new Set([".ts", ".tsx"]);

function walkFiles(start: string) {
  const pending = [start];
  const files: string[] = [];
  while (pending.length) {
    const current = pending.pop()!;
    if (!fs.existsSync(current)) continue;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (entry.name === "node_modules" || entry.name === ".next") continue;
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) pending.push(absolute);
      else if (sourceExtensions.has(path.extname(entry.name))) files.push(absolute);
    }
  }
  return files.sort();
}

function read(relativeOrAbsolute: string) {
  const absolute = path.isAbsolute(relativeOrAbsolute) ? relativeOrAbsolute : path.join(root, relativeOrAbsolute);
  return fs.readFileSync(absolute, "utf8");
}

function relative(filePath: string) {
  return path.relative(root, filePath).replaceAll(path.sep, "/");
}

function importsApp(source: string) {
  return /from\s+["']@\/app\//.test(source) || /import\(["']@\/app\//.test(source) || /from\s+["'](?:\.\.\/)+app\//.test(source);
}

const legacyAllowedFeatureAppImports = new Set<string>([
  "features/inbox/actions/index.ts",
  "features/inbox/components/ConversationDetail.tsx",
  "features/inbox/components/ConversationList.tsx",
  "features/inbox/components/InboxFilters.tsx",
  "features/inbox/components/InboxMetrics.tsx",
  "features/inbox/components/InboxShell.tsx",
  "features/inbox/components/inboxViewHelpers.ts",
  "features/inbox/server/getInboxPageModel.ts",
  "features/integrations/actions/index.ts",
  "features/integrations/components/IntegrationStats.tsx",
  "features/integrations/components/IntegrationsShell.tsx",
  "features/integrations/configuration/ConfigurationSection.tsx",
  "features/integrations/configuration/CredentialsSection.tsx",
  "features/integrations/observability/ObservabilitySection.tsx",
  "features/integrations/risk/RiskSection.tsx",
  "features/integrations/sync/StatusSection.tsx",
  "features/integrations/sync/SyncSection.tsx",
  "features/integrations/server/getIntegrationsPageModel.ts",
  "features/vertical-selection/components/SubverticalPanel.tsx",
  "features/vertical-selection/components/TransactionalMotorPanel.tsx",
  "features/vertical-selection/components/VerticalCatalog.tsx",
  "features/vertical-selection/components/VerticalProfile.tsx",
  "features/vertical-selection/components/VerticalReadiness.tsx",
  "features/vertical-selection/components/VerticalsShell.tsx",
  "features/vertical-selection/server/getVerticalsPageModel.ts",
]);

test("bot studio feature code has no direct app imports", () => {
  const offenders = walkFiles(path.join(root, "features/bot-studio"))
    .filter((file) => importsApp(read(file)))
    .map(relative);
  assert.deepEqual(offenders, []);
});

test("new feature app imports cannot appear outside the legacy debt allowlist", () => {
  const offenders = walkFiles(path.join(root, "features"))
    .map((file) => ({ file: relative(file), source: read(file) }))
    .filter(({ file, source }) => importsApp(source) && !legacyAllowedFeatureAppImports.has(file))
    .map(({ file }) => file);
  assert.deepEqual(offenders, [], offenders.join("\n"));
});

test("app lib data does not import app bot-studio internals", () => {
  const offenders = walkFiles(path.join(root, "app/lib/data"))
    .map((file) => ({ file: relative(file), source: read(file) }))
    .filter(({ source }) => /app\/bot-studio|@\/app\/bot-studio/.test(source))
    .map(({ file }) => file);
  assert.deepEqual(offenders, []);
});

test("bot-studio page files stay as routing shells without payload builders", () => {
  const pageFiles = walkFiles(path.join(root, "app/bot-studio")).filter((file) => file.endsWith("page.tsx"));
  const offenders = pageFiles
    .map((file) => ({ file: relative(file), source: read(file) }))
    .filter(({ source }) => /build[A-Z][A-Za-z0-9]+Payload|payloads?\s*=|apiFetch|fetch\(/.test(source))
    .map(({ file }) => file);
  assert.deepEqual(offenders, []);
});

test("bot-studio page files stay thin and delegate business logic", () => {
  const pageFiles = walkFiles(path.join(root, "app/bot-studio")).filter((file) => file.endsWith("page.tsx"));
  const offenders = pageFiles
    .map((file) => ({ file: relative(file), lineCount: read(file).split(/\r?\n/).length }))
    .filter(({ lineCount }) => lineCount > 90)
    .map(({ file, lineCount }) => `${file} (${lineCount} lines)`);
  assert.deepEqual(offenders, []);
});
