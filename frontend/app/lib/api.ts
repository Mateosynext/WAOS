import { cookies } from "next/headers";
import { ACCESS_COOKIE, refreshAccessToken } from "./session";
import { explainMissingApiBase, getClientApiBase, getFrontendEnvConfig, getServerApiBase } from "./env";
import { unwrapApiEnvelope } from "./contracts";

const ENV = getFrontendEnvConfig();

export class ApiRequestError extends Error {
  status: number | null;
  code: string;
  retryable: boolean;
  constructor(message: string, options: { status?: number | null; code?: string; retryable?: boolean } = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status ?? null;
    this.code = options.code || "api_error";
    this.retryable = Boolean(options.retryable);
  }
}

export type ApiResult<T> = { ok: true; data: T; error: null } | { ok: false; data: null; error: ApiRequestError };

function shouldRetry(error: unknown) {
  if (error instanceof ApiRequestError) return error.retryable;
  if (error instanceof Error) return /abort|timeout|network/i.test(error.message);
  return false;
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readError(response: Response): Promise<ApiRequestError> {
  let message = `La API respondió con ${response.status}.`;
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") message = data.detail;
    else if (typeof data?.message === "string") message = data.message;
    else if (typeof data?.error === "string") message = data.error;
    else if (data?.detail?.message) message = data.detail.message;
  } catch {
    const text = await response.text().catch(() => "");
    if (text) message = text;
  }
  return new ApiRequestError(message, {
    status: response.status,
    code: response.status >= 500 ? "server_error" : response.status === 401 ? "unauthorized" : "request_error",
    retryable: response.status >= 500 || response.status === 429,
  });
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = ENV.timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiRequestError("La solicitud tardó demasiado y se canceló.", { code: "timeout", retryable: true });
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function refreshClientSession(): Promise<string | null> {
  try {
    const response = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-waos-refresh": "1" },
      cache: "no-store",
      credentials: "same-origin",
    });
    if (!response.ok) return null;
    const data = await response.json();
    return typeof data?.access_token === "string" ? data.access_token : null;
  } catch {
    return null;
  }
}

async function requestJson<T>(base: string | null, path: string, init: RequestInit = {}, authToken?: string | null): Promise<T> {
  if (!base) throw new ApiRequestError(explainMissingApiBase(authToken === undefined ? "client" : "server"), { code: "missing_api_base" });
  const headers = new Headers(init.headers || {});
  const serverMode = authToken !== undefined;
  let bearer = authToken || null;
  if (bearer) headers.set("Authorization", `Bearer ${bearer}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let refreshedOnce = false;
  let lastError: unknown = null;
  for (let attempt = 0; attempt <= ENV.retries; attempt += 1) {
    try {
      const response = await fetchWithTimeout(`${base}${path}`, { ...init, headers, cache: "no-store" });
      if (response.status === 401 && !refreshedOnce) {
        refreshedOnce = true;
        const nextToken = serverMode ? (await refreshAccessToken())?.accessToken ?? null : await refreshClientSession();
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
      if (attempt >= ENV.retries || !shouldRetry(error)) break;
      await wait(250 * (attempt + 1));
    }
  }
  if (lastError instanceof ApiRequestError) throw lastError;
  if (lastError instanceof Error) throw new ApiRequestError(lastError.message, { code: "network_error", retryable: true });
  throw new ApiRequestError("No se pudo completar la solicitud.", { code: "unknown_error" });
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value || null;
  return requestJson<T>(getServerApiBase(), path, init, accessToken);
}

export async function apiFetchResult<T>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await apiFetch<T>(path, init), error: null };
  } catch (error) {
    const apiError = error instanceof ApiRequestError ? error : new ApiRequestError(error instanceof Error ? error.message : "No se pudo completar la solicitud.");
    return { ok: false, data: null, error: apiError };
  }
}

export async function apiFetchOrDefault<T>(path: string, fallback: T, init: RequestInit = {}): Promise<T> {
  const result = await apiFetchResult<T>(path, init);
  return result.ok ? result.data : fallback;
}

export async function clientApiFetchResult<T>(path: string, init: RequestInit = {}): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await requestJson<T>(getClientApiBase(), path, init), error: null };
  } catch (error) {
    const apiError = error instanceof ApiRequestError ? error : new ApiRequestError(error instanceof Error ? error.message : "No se pudo completar la solicitud.");
    return { ok: false, data: null, error: apiError };
  }
}
