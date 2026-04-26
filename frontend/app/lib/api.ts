import "server-only";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, getCurrentBotId, getCurrentOrganizationId, refreshAccessToken } from "./session";
import { refreshBrowserSession } from "./auth/refresh";
import { explainMissingApiBase, getClientApiBase, getFrontendEnvConfig, getServerApiBase } from "./env";
import { unwrapApiEnvelope } from "./contracts/shared";

const ENV = getFrontendEnvConfig();

export class ApiRequestError extends Error {
  status: number | null;
  code: string;
  retryable: boolean;
  requestId: string | null;
  correlationId: string | null;
  details: unknown;
  constructor(message: string, options: { status?: number | null; code?: string; retryable?: boolean; requestId?: string | null; correlationId?: string | null; details?: unknown } = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status ?? null;
    this.code = options.code || "api_error";
    this.retryable = Boolean(options.retryable);
    this.requestId = options.requestId ?? null;
    this.correlationId = options.correlationId ?? null;
    this.details = options.details ?? null;
  }
}

export type ApiResult<T> = { ok: true; data: T; error: null } | { ok: false; data: null; error: ApiRequestError };
export type ApiRequestInit = RequestInit & { timeoutMs?: number | null };

function methodAllowsRetry(method: string | null | undefined) {
  return ["GET", "HEAD", "OPTIONS"].includes(String(method || "GET").toUpperCase());
}

function shouldRetry(error: unknown, method?: string | null) {
  if (!methodAllowsRetry(method)) return false;
  if (error instanceof ApiRequestError) return error.retryable;
  if (error instanceof Error) return /abort|timeout|network/i.test(error.message);
  return false;
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readError(response: Response): Promise<ApiRequestError> {
  let message = `La API respondió con ${response.status}.`;
  let code = response.status >= 500 ? "server_error" : response.status === 401 ? "unauthorized" : "request_error";
  let requestId = response.headers.get("x-request-id");
  let correlationId = response.headers.get("x-correlation-id");
  let details: unknown = null;
  const text = await response.text().catch(() => "");
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (data) {
    if (typeof data?.detail === "string") message = data.detail;
    else if (typeof data?.message === "string") message = data.message;
    else if (typeof data?.error === "string") message = data.error;
    else if (typeof data?.error?.message === "string") message = data.error.message;
    else if (data?.detail?.message) message = data.detail.message;
    if (typeof data?.error?.code === "string") code = data.error.code;
    else if (typeof data?.detail?.code === "string") code = data.detail.code;
    else if (typeof data?.code === "string") code = data.code;
    requestId = typeof data?.request_id === "string" ? data.request_id : requestId;
    correlationId = typeof data?.correlation_id === "string" ? data.correlation_id : correlationId;
    details = data?.error?.details ?? data?.details ?? data?.detail ?? null;
  } else if (text) {
    message = text.length > 1200 ? text.slice(0, 1200) + "...[truncated]" : text;
  }
  return new ApiRequestError(message, {
    status: response.status,
    code,
    retryable: response.status >= 500 || response.status === 429,
    requestId,
    correlationId,
    details,
  });
}

async function fetchWithTimeout(input: RequestInfo | URL, init: ApiRequestInit = {}, timeoutMs = ENV.timeoutMs) {
  const controller = new AbortController();
  const upstreamSignal = init.signal;
  const resolvedTimeoutMs = Math.max(Number(timeoutMs) || ENV.timeoutMs, ENV.timeoutMs, 1000);
  const forwardAbort = () => controller.abort(upstreamSignal?.reason);
  if (upstreamSignal?.aborted) forwardAbort();
  upstreamSignal?.addEventListener("abort", forwardAbort, { once: true });
  const timeout = setTimeout(() => controller.abort(new DOMException("Request timeout", "AbortError")), resolvedTimeoutMs);
  try {
    const { timeoutMs: _timeoutMs, signal: _signal, ...rest } = init;
    return await fetch(input, { ...rest, signal: controller.signal });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      if (upstreamSignal?.aborted) throw error;
      throw new ApiRequestError("La solicitud tardó demasiado y se canceló.", { code: "timeout", retryable: true });
    }
    throw error;
  } finally {
    clearTimeout(timeout);
    upstreamSignal?.removeEventListener("abort", forwardAbort);
  }
}

async function buildContextHeaders(serverMode: boolean, headers: Headers, method: string) {
  headers.set("x-waos-frontend", "internal-console");
  headers.set("x-waos-request-method", method);
  const requestId = headers.get("x-request-id") || `web-${crypto.randomUUID()}`;
  headers.set("x-request-id", requestId);
  headers.set("x-correlation-id", headers.get("x-correlation-id") || requestId);
  if (!serverMode) return;
  const [organizationId, botId] = await Promise.all([getCurrentOrganizationId(), getCurrentBotId()]);
  if (organizationId) {
    headers.set("x-waos-org-id", organizationId);
    headers.set("x-organization-id", organizationId);
  }
  if (botId) {
    headers.set("x-waos-bot-id", botId);
    headers.set("x-bot-id", botId);
  }
}

async function requestJson<T>(base: string | null, path: string, init: ApiRequestInit = {}, authToken?: string | null): Promise<T> {
  if (!base) throw new ApiRequestError(explainMissingApiBase(authToken === undefined ? "client" : "server"), { code: "missing_api_base" });
  const headers = new Headers(init.headers || {});
  const serverMode = authToken !== undefined;
  const method = String(init.method || "GET").toUpperCase();
  let bearer = authToken || null;
  if (bearer) headers.set("Authorization", `Bearer ${bearer}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  await buildContextHeaders(serverMode, headers, method);
  let refreshedOnce = false;
  let lastError: unknown = null;
  for (let attempt = 0; attempt <= ENV.retries; attempt += 1) {
    try {
      const response = await fetchWithTimeout(`${base}${path}`, { ...init, method, headers, cache: "no-store" }, init.timeoutMs ?? ENV.timeoutMs);
      if (response.status === 401 && !refreshedOnce) {
        refreshedOnce = true;
        const nextToken = serverMode ? (await refreshAccessToken())?.accessToken ?? null : (await refreshBrowserSession())?.accessToken ?? null;
        if (nextToken) {
          headers.set("Authorization", `Bearer ${nextToken}`);
          continue;
        }
      }
      if (!response.ok) throw await readError(response);
      if (response.status === 204) return null as T;
      const payload = (await response.json()) as T;
      return unwrapApiEnvelope(payload) as T;
    } catch (error) {
      lastError = error;
      if (attempt >= ENV.retries || !shouldRetry(error, method)) break;
      await wait(250 * (attempt + 1));
    }
  }
  if (lastError instanceof ApiRequestError) throw lastError;
  if (lastError instanceof Error) throw new ApiRequestError(lastError.message, { code: "network_error", retryable: true });
  throw new ApiRequestError("No se pudo completar la solicitud.", { code: "unknown_error" });
}

export async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value || null;
  return requestJson<T>(getServerApiBase(), path, init, accessToken);
}

export async function apiFetchResult<T>(path: string, init: ApiRequestInit = {}): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await apiFetch<T>(path, init), error: null };
  } catch (error) {
    const apiError = error instanceof ApiRequestError ? error : new ApiRequestError(error instanceof Error ? error.message : "No se pudo completar la solicitud.");
    return { ok: false, data: null, error: apiError };
  }
}

export async function apiFetchOrDefault<T>(path: string, fallback: T, init: ApiRequestInit = {}): Promise<T> {
  const result = await apiFetchResult<T>(path, init);
  return result.ok ? result.data : fallback;
}

export async function clientApiFetchResult<T>(path: string, init: ApiRequestInit = {}): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await requestJson<T>(getClientApiBase(), path, init), error: null };
  } catch (error) {
    const apiError = error instanceof ApiRequestError ? error : new ApiRequestError(error instanceof Error ? error.message : "No se pudo completar la solicitud.");
    return { ok: false, data: null, error: apiError };
  }
}
