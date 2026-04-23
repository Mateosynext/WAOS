import { getServerApiBase } from "../env";
import { AUTH_REFRESH_PATH } from "./shared-session";

export type RefreshedSessionTokens = {
  accessToken: string;
  refreshToken: string;
  session?: unknown;
};

export function isRefreshedSessionPayload(value: unknown): value is { access_token: string; refresh_token: string; session?: unknown } {
  return Boolean(value)
    && typeof value === "object"
    && typeof (value as { access_token?: unknown }).access_token === "string"
    && typeof (value as { refresh_token?: unknown }).refresh_token === "string";
}

export async function requestSessionRefresh(refreshToken: string, apiBase = getServerApiBase()): Promise<RefreshedSessionTokens | null> {
  if (!refreshToken || !apiBase) return null;
  try {
    const response = await fetch(`${apiBase}${AUTH_REFRESH_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) return null;
    const payload = await response.json().catch(() => null);
    if (!isRefreshedSessionPayload(payload)) return null;
    return {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      session: payload.session ?? null,
    };
  } catch {
    return null;
  }
}

export async function refreshBrowserSession(): Promise<RefreshedSessionTokens | null> {
  try {
    const response = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-waos-refresh": "1" },
      cache: "no-store",
      credentials: "same-origin",
    });
    if (!response.ok) return null;
    const payload = await response.json().catch(() => null);
    if (!isRefreshedSessionPayload(payload)) return null;
    return {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      session: payload.session ?? null,
    };
  } catch {
    return null;
  }
}
