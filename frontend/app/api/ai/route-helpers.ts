import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, getCurrentBotId, getCurrentOrganizationId, refreshAccessToken } from "@/app/lib/session";
import { getServerApiBase } from "@/app/lib/env";

const DEFAULT_PROXY_TIMEOUT_MS = 60_000;
const LONG_RUNNING_PROXY_TIMEOUT_MS = 120_000;

function proxyTimeoutFor(backendPath: string) {
  return /\/(apply|prepare-apply|prepare-canary|go-live-readiness)$/.test(backendPath) ? LONG_RUNNING_PROXY_TIMEOUT_MS : DEFAULT_PROXY_TIMEOUT_MS;
}

export async function getBearerToken() {
  const store = await cookies();
  return store.get(ACCESS_COOKIE)?.value || (await refreshAccessToken())?.accessToken || "";
}

function safeTextPreview(text: string) {
  return text.length > 900 ? `${text.slice(0, 900)}...[truncated]` : text;
}

function parseMaybeJson(text: string) {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function upstreamErrorPayload(status: number, backendPath: string, text: string) {
  const parsed = parseMaybeJson(text);
  if (parsed) return parsed;
  const code = status === 404 ? "backend_route_not_found" : "backend_upstream_error";
  const message = status === 404
    ? `Backend no encontro ${backendPath}. Redeploya el backend correcto antes de probar el bot.`
    : safeTextPreview(text || "Backend upstream error");
  return { detail: { code, message, upstream_status: status, backend_path: backendPath } };
}

async function buildTenantProxyHeaders(request: Request, contentType: string, token: string) {
  const requestId = request.headers.get("x-request-id") || `web-ai-${crypto.randomUUID()}`;
  const correlationId = request.headers.get("x-correlation-id") || requestId;
  const [organizationId, botId] = await Promise.all([getCurrentOrganizationId(), getCurrentBotId()]);
  return {
    "Content-Type": contentType,
    "Accept": request.headers.get("accept") || "application/json",
    "X-WAOS-Frontend-Proxy": "ai-workflows",
    "X-Request-Id": requestId,
    "X-Correlation-Id": correlationId,
    ...(organizationId ? { "X-WAOS-Org-Id": organizationId, "X-Organization-Id": organizationId } : {}),
    ...(botId ? { "X-WAOS-Bot-Id": botId, "X-Bot-Id": botId } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function proxyJson(request: Request, backendPath: string, method = request.method) {
  const base = getServerApiBase();
  if (!base) return NextResponse.json({ detail: { message: "Backend API base missing", code: "missing_api_base" } }, { status: 500 });
  const token = await getBearerToken();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();
  const contentType = request.headers.get("content-type") || "application/json";
  const url = new URL(request.url);
  const upstreamPath = `${backendPath}${url.search || ""}`;
  const proxyTimeoutMs = proxyTimeoutFor(backendPath);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), proxyTimeoutMs);
  try {
    const response = await fetch(`${base}${upstreamPath}`, {
      method,
      body,
      headers: await buildTenantProxyHeaders(request, contentType, token),
      cache: "no-store",
      signal: controller.signal,
    });
    const text = await response.text();
    const payloadText = response.ok ? (text || "{}") : JSON.stringify(upstreamErrorPayload(response.status, backendPath, text));
    return new NextResponse(payloadText, {
      status: response.status,
      headers: {
        "Content-Type": response.ok ? (response.headers.get("content-type") || "application/json") : "application/json",
        "Cache-Control": "no-store",
        "X-WAOS-Backend-Path": backendPath,
        "X-Request-Id": response.headers.get("x-request-id") || response.headers.get("x-correlation-id") || "",
        "X-Correlation-Id": response.headers.get("x-correlation-id") || response.headers.get("x-request-id") || "",
      },
    });
  } catch (error) {
    const aborted = error instanceof DOMException && error.name === "AbortError";
    const message = aborted ? `Backend timeout despues de ${proxyTimeoutMs / 1000}s` : error instanceof Error ? error.message : "Backend proxy failed";
    return NextResponse.json({ detail: { code: aborted ? "backend_timeout" : "backend_unreachable", message, backend_path: backendPath } }, { status: 502 });
  } finally {
    clearTimeout(timeout);
  }
}
