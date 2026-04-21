import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const frontendRoot = process.cwd();

function read(relativePath: string) {
  return fs.readFileSync(path.join(frontendRoot, relativePath), "utf8");
}

test("waos compatibility barrel uses explicit exports only", () => {
  const waosBarrel = read("app/lib/waos.ts");
  assert.match(waosBarrel, /Deprecated compatibility barrel/);
  assert.doesNotMatch(waosBarrel, /export \* from /);
  assert.match(waosBarrel, /export \{[\s\S]*getBots[\s\S]*\} from "\.\/data\/bots"/);
  assert.match(waosBarrel, /export \{[\s\S]*getVerticalProfile[\s\S]*\} from "\.\/data\/verticals"/);
});

test("wizard route response preserves transport metadata", () => {
  const helper = read("app/api/onboarding/wizard/route-helpers.ts");
  assert.match(helper, /X-Request-Id/);
  assert.match(helper, /X-Correlation-Id/);
  assert.match(helper, /X-Error-Code/);
  assert.match(helper, /error_type/);
  assert.match(helper, /request_id/);
  assert.match(helper, /correlation_id/);
  assert.match(helper, /status,/);
});
