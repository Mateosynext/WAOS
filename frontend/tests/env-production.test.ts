import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("frontend env helper no longer hardcodes old production hosts", () => {
  const source = read("app/lib/env.ts");
  assert.doesNotMatch(source, /onrender\.com/);
  assert.doesNotMatch(source, /vercel\.app/);
  assert.match(source, /allowDevFallback/);
  assert.match(source, /NODE_ENV !== \"production\"/);
});

test("production build validates env before next build", () => {
  const pkg = JSON.parse(read("package.json"));
  assert.match(String(pkg.scripts.build), /validate-env\.mjs/);
});
