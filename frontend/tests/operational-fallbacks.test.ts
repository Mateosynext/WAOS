import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
function read(rel: string) { return fs.readFileSync(path.join(root, rel), "utf8"); }

test("frontend fallbacks emit telemetry and critical fallbacks fail closed", () => {
  const api = read("app/lib/api.ts");
  assert.match(api, /export async function recordApiFallback/);
  assert.match(api, /kind:\s*"api_fallback"/);
  assert.match(api, /frontend\.api_fallback/);
  assert.match(api, /severity === "critical"/);
  assert.match(api, /throw new ApiRequestError\(`Backend unavailable for critical frontend data/);
});

test("shared data state helpers expose degraded state instead of silent fallback", () => {
  const shared = read("app/lib/data/shared.ts");
  assert.match(shared, /fetchArrayState/);
  assert.match(shared, /fetchRecordState/);
  assert.match(shared, /recordApiFallback\(endpoint, result\.error/);
  assert.match(shared, /ok: false/);
});

test("operational dashboards block when critical backend data is degraded", () => {
  for (const rel of ["app/status/page.tsx", "app/operations/page.tsx", "app/scheduler/page.tsx", "app/insights/page.tsx"]) {
    const source = read(rel);
    assert.match(source, /OperationalDegradedBanner/, `${rel} must render degraded backend state`);
    assert.match(source, /hasOperationalFailures/, `${rel} must check critical state failures`);
    assert.match(source, /block/, `${rel} must block critical dashboard data on failure`);
    assert.doesNotMatch(source, /apiFetchOrDefault/, `${rel} must not fetch critical data through fallback-only helper`);
  }
});
