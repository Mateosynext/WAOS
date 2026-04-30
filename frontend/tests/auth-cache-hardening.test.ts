import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildScopedHeaders, PRIVATE_APP_CACHE_HEADERS, PUBLIC_DOCUMENT_CACHE_HEADERS } from "../app/lib/http/cache-policy.ts";
import { describeRouteAccess, MIDDLEWARE_MATCHER } from "../app/lib/auth/route-policy.ts";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath: string) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

test("route policy distinguishes public, org-scoped and role-guarded routes", () => {
  assert.deepEqual(describeRouteAccess("/legal"), {
    isPublic: true,
    isAuthPage: false,
    requiresOrganization: false,
    allowedRoles: null,
  });

  assert.deepEqual(describeRouteAccess("/login"), {
    isPublic: true,
    isAuthPage: true,
    requiresOrganization: false,
    allowedRoles: null,
  });

  assert.deepEqual(describeRouteAccess("/bot-studio"), {
    isPublic: false,
    isAuthPage: false,
    requiresOrganization: true,
    allowedRoles: null,
  });

  assert.deepEqual(describeRouteAccess("/security"), {
    isPublic: false,
    isAuthPage: false,
    requiresOrganization: true,
    allowedRoles: ["super_admin", "admin", "security_admin", "ops_admin"],
  });

  assert.deepEqual(MIDDLEWARE_MATCHER, ["/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|.*\\..*).*)"]);
});

test("edge session helper hardens auth beyond cookie presence", () => {
  const edgeSession = read("app/lib/auth/edge-session.ts");

  assert.match(edgeSession, /decodeAccessTokenClaims/);
  assert.match(edgeSession, /isExpiredJwt/);
  assert.match(edgeSession, /requestSessionRefresh/);
  assert.match(edgeSession, /fetchSessionUserFromApi/);
  assert.match(edgeSession, /from "\.\/shared-session\.ts"/);
  assert.match(edgeSession, /selectedOrganizationId/);
});

test("cache policy scopes auth, public docs and private app headers without global no-store", () => {
  const headers = buildScopedHeaders();
  const nextConfig = read("next.config.ts");
  const cachePolicy = read("app/lib/http/cache-policy.ts");

  assert.ok(headers.some((entry) => entry.source === "/legal" && entry.headers === PUBLIC_DOCUMENT_CACHE_HEADERS));
  assert.ok(headers.some((entry) => entry.source === "/login"));
  assert.ok(headers.some((entry) => entry.source === "/api/:path*"));
  assert.ok(headers.some((entry) => entry.source === "/bot-studio/:path*" && entry.headers === PRIVATE_APP_CACHE_HEADERS));

  assert.match(nextConfig, /buildScopedHeaders/);
  assert.match(cachePolicy, /private, no-cache, max-age=0, must-revalidate/);
  assert.doesNotMatch(cachePolicy, /source: "\/:path\*"[\s\S]*Cache-Control", value: "no-store"/);
});

test("middleware uses verified session flow instead of cookie-presence-only auth", () => {
  const middleware = read("middleware.ts");

  assert.match(middleware, /verifyRequestSession/);
  assert.match(middleware, /describeRouteAccess/);
  assert.match(middleware, /routeAccess\.requiresOrganization/);
  assert.match(middleware, /routeAccess\.allowedRoles/);
  assert.match(middleware, /redirect\.cookies\.delete\(ACCESS_COOKIE\)/);
  assert.doesNotMatch(middleware, /if \(!token\)/);
  assert.doesNotMatch(middleware, /pathname\.startsWith\("\/login"\)/);
});
