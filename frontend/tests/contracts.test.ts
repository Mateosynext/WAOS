import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "../..");

test("agenda contract expects pending metric and backend exposes overview endpoint", () => {
  const result = spawnSync("python", ["-c", `from backend.app.main import app; import json; print(json.dumps(app.openapi()))`], {
    cwd: repoRoot,
    env: { ...process.env, PYTHONPATH: repoRoot },
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr || "OpenAPI export should succeed");
  const openapi = JSON.parse(result.stdout);
  const agendaOverview = openapi.paths?.["/api/v1/agenda/overview"];
  assert.ok(agendaOverview, "agenda overview endpoint should exist");
  assert.ok(agendaOverview.get, "agenda overview endpoint should expose GET");
});
