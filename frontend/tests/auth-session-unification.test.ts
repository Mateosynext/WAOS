import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("server and edge session helpers share auth endpoints and org resolution", () => {
  const shared = read("app/lib/auth/shared-session.ts");
  const serverSession = read("app/lib/session.ts");
  const edgeSession = read("app/lib/auth/edge-session.ts");
  const refresh = read("app/lib/auth/refresh.ts");

  assert.match(shared, /AUTH_ME_PATH/);
  assert.match(shared, /AUTH_REFRESH_PATH/);
  assert.match(shared, /resolveSessionOrganizationId/);
  assert.match(shared, /fetchSessionUserFromApi/);

  assert.match(serverSession, /from "\.\/auth\/shared-session"/);
  assert.match(serverSession, /resolveSessionOrganizationId/);
  assert.match(serverSession, /fetchSessionUserFromApi/);

  assert.match(edgeSession, /from "\.\/shared-session\.ts"/);
  assert.match(edgeSession, /resolveSessionOrganizationId/);
  assert.match(edgeSession, /fetchSessionUserFromApi/);

  assert.match(refresh, /AUTH_REFRESH_PATH/);
  assert.doesNotMatch(serverSession, /\/api\/v1\/auth\/me/);
  assert.doesNotMatch(edgeSession, /\/api\/v1\/auth\/me/);
  assert.doesNotMatch(refresh, /\/api\/v1\/auth\/refresh/);
});
