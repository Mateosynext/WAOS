const SCRIPT_SRC = "script-src 'self'";

export const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "form-action 'self'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  SCRIPT_SRC,
  "connect-src 'self' https: wss:",
  "media-src 'self' blob: data: https:",
  "worker-src 'self' blob:",
].join("; ");

export const baseSecurityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
];

export const securityHeaders = [
  ...baseSecurityHeaders,
  { key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY },
];

export const documentSecurityHeaders = baseSecurityHeaders;

const PRIVATE_ROUTE_SOURCES = [
  "/",
  "/agenda/:path*",
  "/audit/:path*",
  "/bot-studio/:path*",
  "/bots/:path*",
  "/business-hub/:path*",
  "/catalog/:path*",
  "/client/:path*",
  "/commerce-insights/:path*",
  "/design-system/:path*",
  "/flows/:path*",
  "/inbox/:path*",
  "/insights/:path*",
  "/integrations/:path*",
  "/launch-center/:path*",
  "/logs/:path*",
  "/media/:path*",
  "/omnichannel/:path*",
  "/onboarding/:path*",
  "/operations/:path*",
  "/organizations/:path*",
  "/policies/:path*",
  "/promotions/:path*",
  "/releases/:path*",
  "/revenue/:path*",
  "/runs/:path*",
  "/scheduler/:path*",
  "/search/:path*",
  "/security/:path*",
  "/secrets/:path*",
  "/status/:path*",
  "/studio/:path*",
  "/support/:path*",
  "/usage/:path*",
  "/vacantes/:path*",
  "/verticals/:path*",
  "/v14/:path*",
  "/v15/:path*",
  "/v16/:path*",
];

export const STATIC_CACHE_HEADERS = [
  ...securityHeaders,
  { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
  { key: "Vary", value: "Accept-Encoding" },
];

export const SEMISTATIC_CACHE_HEADERS = [
  ...securityHeaders,
  { key: "Cache-Control", value: "public, max-age=86400, stale-while-revalidate=604800" },
  { key: "Vary", value: "Accept-Encoding" },
];

export const PUBLIC_DOCUMENT_CACHE_HEADERS = [
  ...documentSecurityHeaders,
  { key: "Cache-Control", value: "public, max-age=300, stale-while-revalidate=3600" },
  { key: "Vary", value: "Accept-Encoding" },
];

export const AUTH_FLOW_CACHE_HEADERS = [
  ...documentSecurityHeaders,
  { key: "Cache-Control", value: "no-store" },
  { key: "Vary", value: "Cookie, Accept-Encoding" },
];

export const PRIVATE_APP_CACHE_HEADERS = [
  ...documentSecurityHeaders,
  { key: "Cache-Control", value: "private, no-cache, max-age=0, must-revalidate" },
  { key: "Vary", value: "Cookie, Accept-Encoding" },
];

export const API_CACHE_HEADERS = [
  ...securityHeaders,
  { key: "Cache-Control", value: "no-store" },
  { key: "Vary", value: "Origin, Cookie, Accept-Encoding" },
];

export function buildScopedHeaders() {
  return [
    {
      source: "/_next/static/:path*",
      headers: STATIC_CACHE_HEADERS,
    },
    {
      source: "/static/:path*",
      headers: SEMISTATIC_CACHE_HEADERS,
    },
    {
      source: "/legal",
      headers: PUBLIC_DOCUMENT_CACHE_HEADERS,
    },
    {
      source: "/legal/:path*",
      headers: PUBLIC_DOCUMENT_CACHE_HEADERS,
    },
    {
      source: "/login",
      headers: AUTH_FLOW_CACHE_HEADERS,
    },
    {
      source: "/login/:path*",
      headers: AUTH_FLOW_CACHE_HEADERS,
    },
    {
      source: "/api/:path*",
      headers: API_CACHE_HEADERS,
    },
    ...PRIVATE_ROUTE_SOURCES.map((source) => ({
      source,
      headers: PRIVATE_APP_CACHE_HEADERS,
    })),
  ];
}
