import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("status support and launch-center are real pages instead of redirects", () => {
  const status = read("app/status/page.tsx");
  const support = read("app/support/page.tsx");
  const launchCenter = read("app/launch-center/page.tsx");

  assert.doesNotMatch(status, /redirect\(/);
  assert.doesNotMatch(support, /redirect\(/);
  assert.doesNotMatch(launchCenter, /redirect\(/);
  assert.match(status, /Estado interno/);
  assert.match(support, /Soporte operativo/);
  assert.match(launchCenter, /Launch center/);
});

test("api layer sends internal console context and only retries safe methods", () => {
  const api = read("app/lib/api.ts");
  assert.match(api, /x-waos-frontend/);
  assert.match(api, /x-waos-request-method/);
  assert.match(api, /x-waos-org-id/);
  assert.match(api, /x-waos-bot-id/);
  assert.match(api, /GET", "HEAD", "OPTIONS/);
});

test("session keeps org and bot scope consistent", () => {
  const session = read("app/lib/session.ts");
  assert.match(session, /keepScopeConsistent/);
  assert.match(session, /store\.delete\(BOT_COOKIE\)/);
});

test("critical chrome uses tokenized surfaces in refactored screens", () => {
  const login = read("app/login/page.tsx");
  const recovery = read("app/login/recovery/page.tsx");
  const errorBoundary = read("app/error.tsx");
  const notFound = read("app/not-found.tsx");
  const commandPalette = read("app/components/CommandPalette.tsx");

  assert.match(login, /var\(--client-shell-bg\)/);
  assert.match(recovery, /var\(--client-shell-bg\)/);
  assert.match(errorBoundary, /var\(--client-shell-bg\)/);
  assert.match(notFound, /var\(--client-shell-bg\)/);
  assert.match(commandPalette, /var\(--surface-subtle\)/);
});
