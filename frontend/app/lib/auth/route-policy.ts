export const MIDDLEWARE_MATCHER = ["/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|.*\\..*).*)"];

const PUBLIC_EXACT = new Set(["/login", "/login/recovery", "/legal"]);
const PUBLIC_PREFIXES = ["/legal/"];
const AUTH_PAGES = new Set(["/login", "/login/recovery"]);
const ORG_REQUIRED_PREFIXES = [
  "/agenda",
  "/bot-studio",
  "/bots",
  "/business-hub",
  "/catalog",
  "/client",
  "/commerce-insights",
  "/flows",
  "/inbox",
  "/insights",
  "/integrations",
  "/launch-center",
  "/media",
  "/omnichannel",
  "/onboarding",
  "/operations",
  "/policies",
  "/promotions",
  "/releases",
  "/revenue",
  "/runs",
  "/scheduler",
  "/search",
  "/security",
  "/secrets",
  "/studio",
  "/support",
  "/usage",
  "/vacantes",
  "/verticals",
];

const ROLE_RULES = [
  {
    prefixes: ["/security"],
    roles: ["super_admin", "admin", "security_admin", "ops_admin"],
  },
  {
    prefixes: ["/secrets"],
    roles: ["super_admin", "admin", "security_admin"],
  },
  {
    prefixes: ["/status", "/operations"],
    roles: ["super_admin", "admin", "ops_admin", "support", "security_admin"],
  },
];

function matchesPrefix(pathname: string, prefix: string) {
  return pathname === prefix || pathname.startsWith(`${prefix}/`) || pathname.startsWith(`${prefix}?`);
}

export function isPublicRoute(pathname: string) {
  return PUBLIC_EXACT.has(pathname) || PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function isAuthPage(pathname: string) {
  return AUTH_PAGES.has(pathname);
}

export function requiresOrganization(pathname: string) {
  return ORG_REQUIRED_PREFIXES.some((prefix) => matchesPrefix(pathname, prefix));
}

export function getAllowedRoles(pathname: string): string[] | null {
  const match = ROLE_RULES.find((rule) => rule.prefixes.some((prefix) => matchesPrefix(pathname, prefix)));
  return match?.roles ?? null;
}

export function describeRouteAccess(pathname: string) {
  return {
    isPublic: isPublicRoute(pathname),
    isAuthPage: isAuthPage(pathname),
    requiresOrganization: requiresOrganization(pathname),
    allowedRoles: getAllowedRoles(pathname),
  };
}
