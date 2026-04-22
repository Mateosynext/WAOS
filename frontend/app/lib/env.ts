export type FrontendEnvConfig = {
  clientApiBase: string | null;
  serverApiBase: string | null;
  publicSiteUrl: string | null;
  timeoutMs: number;
  retries: number;
};

const DEV_FALLBACK_CLIENT_API_BASE = "http://localhost:4100";
const DEV_FALLBACK_SERVER_API_BASE = "http://localhost:4100";
const DEV_FALLBACK_PUBLIC_SITE_URL = "http://localhost:3000";
const MIN_API_TIMEOUT_MS = 8000;

function allowDevFallback() {
  return process.env.NODE_ENV !== "production" || process.env.WAOS_ALLOW_ENV_FALLBACK === "true";
}

function cleanUrl(value: string | null | undefined) {
  const raw = String(value || "").trim();
  if (!raw) return null;
  return raw.replace(/\/$/, "");
}

function readNumber(value: string | undefined, fallback: number) {
  const parsed = Number(value || "");
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

export function getClientApiBase() {
  return cleanUrl(process.env.NEXT_PUBLIC_API_BASE_URL) || (allowDevFallback() ? DEV_FALLBACK_CLIENT_API_BASE : null);
}

export function getServerApiBase() {
  return cleanUrl(process.env.API_INTERNAL_URL) || cleanUrl(process.env.API_BASE_URL) || cleanUrl(process.env.NEXT_PUBLIC_API_BASE_URL) || (allowDevFallback() ? DEV_FALLBACK_SERVER_API_BASE : null);
}

export function getPublicSiteUrl() {
  return cleanUrl(process.env.NEXT_PUBLIC_APP_URL) || cleanUrl(process.env.PUBLIC_APP_URL) || (allowDevFallback() ? DEV_FALLBACK_PUBLIC_SITE_URL : null);
}

export function getFrontendEnvConfig(): FrontendEnvConfig {
  return {
    clientApiBase: getClientApiBase(),
    serverApiBase: getServerApiBase(),
    publicSiteUrl: getPublicSiteUrl(),
    timeoutMs: Math.max(readNumber(process.env.API_TIMEOUT_MS, 12000), MIN_API_TIMEOUT_MS),
    retries: readNumber(process.env.API_RETRIES, 1),
  };
}

export function explainMissingApiBase(target: "client" | "server") {
  return target === "client"
    ? "Configura NEXT_PUBLIC_API_BASE_URL para el navegador."
    : "Configura API_INTERNAL_URL o API_BASE_URL para los fetch server-side.";
}
