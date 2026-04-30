import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

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

test("production CSP script-src is locked down", () => {
  const source = read("app/lib/http/cache-policy.ts");
  assert.match(source, /const SCRIPT_SRC = "script-src 'self'"/);
  assert.doesNotMatch(source, /script-src[^\n]*unsafe-inline/);
  assert.doesNotMatch(source, /script-src[^\n]*unsafe-eval/);
});

test("backend dependencies are lock driven", () => {
  const requirements = fs.readFileSync(path.join(root, "..", "backend", "requirements.txt"), "utf8");
  const lock = fs.readFileSync(path.join(root, "..", "backend", "requirements.lock"), "utf8");
  assert.match(requirements, /^-r requirements\.lock/m);
  assert.doesNotMatch(lock, />=/);
  assert.match(lock, /fastapi==/);
  assert.match(lock, /cryptography==/);
});
