export type FrontendEnvConfig = {
  clientApiBase: string | null;
  serverApiBase: string | null;
  publicSiteUrl: string | null;
  timeoutMs: number;
  retries: number;
};

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
  return cleanUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
}

export function getServerApiBase() {
  return cleanUrl(process.env.API_INTERNAL_URL) || cleanUrl(process.env.API_BASE_URL) || cleanUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
}

export function getPublicSiteUrl() {
  return cleanUrl(process.env.NEXT_PUBLIC_APP_URL) || cleanUrl(process.env.PUBLIC_APP_URL);
}

export function getFrontendEnvConfig(): FrontendEnvConfig {
  return {
    clientApiBase: getClientApiBase(),
    serverApiBase: getServerApiBase(),
    publicSiteUrl: getPublicSiteUrl(),
    timeoutMs: readNumber(process.env.API_TIMEOUT_MS, 12000),
    retries: readNumber(process.env.API_RETRIES, 1),
  };
}

export function explainMissingApiBase(target: "client" | "server") {
  return target === "client"
    ? "Configura NEXT_PUBLIC_API_BASE_URL para el navegador."
    : "Configura API_INTERNAL_URL o API_BASE_URL para los fetch server-side.";
}
