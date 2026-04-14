import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const frontendRoot = path.resolve(process.cwd(), "app");

for (const routeName of ["v14", "v15", "v16"]) {
  test(`${routeName} does not live at the active app root`, () => {
    assert.equal(existsSync(path.join(frontendRoot, routeName)), false);
    assert.equal(existsSync(path.join(frontendRoot, "(legacy)", routeName, "page.tsx")), true);
  });
}

test("legacy redirect helper is centralized", () => {
  const helperPath = path.join(frontendRoot, "(legacy)", "_components", "LegacyRouteRedirect.tsx");
  assert.equal(existsSync(helperPath), true);
  const source = readFileSync(helperPath, "utf8");
  assert.match(source, /redirectLegacyRoute/);
  assert.match(source, /redirect\("\/"\)/);
});

test("frontend architecture manifest documents the legacy route policy", () => {
  const manifestPath = path.join(frontendRoot, "lib", "architecture.ts");
  assert.equal(existsSync(manifestPath), true);
  const source = readFileSync(manifestPath, "utf8");
  assert.match(source, /frontend\/app\/\(legacy\)/);
  assert.match(source, /supportedRouteAliases/);
});
