import "server-only";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { normalizeSessionUser, type SessionUser } from "./contracts/auth";
import { getServerApiBase } from "./env";
import { ACCESS_COOKIE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, accessCookieOptions, refreshCookieOptions, sessionCookieOptions, sessionScopeCookieOptions } from "./auth/cookies";

const API_BASE = getServerApiBase();

export type { SessionOrganization } from "./contracts/auth";
export type { SessionUser } from "./contracts/auth";

export { ACCESS_COOKIE, BOT_COOKIE, CSRF_COOKIE, ORG_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "./auth/cookies";


export async function getAccessToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(ACCESS_COOKIE)?.value ?? null;
}

export async function getRefreshToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(REFRESH_COOKIE)?.value ?? null;
}

export async function getCurrentOrganizationId(): Promise<string | null> {
  const store = await cookies();
  return store.get(ORG_COOKIE)?.value ?? null;
}

export async function getCurrentBotId(): Promise<string | null> {
  const store = await cookies();
  return store.get(BOT_COOKIE)?.value ?? null;
}

export async function persistSessionTokens(accessToken: string, refreshToken: string) {
  const store = await cookies();
  try {
    store.set(ACCESS_COOKIE, accessToken, accessCookieOptions());
    store.set(REFRESH_COOKIE, refreshToken, refreshCookieOptions());
  } catch {
    // Some read-only server contexts can still use the refreshed token for the current request.
  }
}

export async function clearSessionCookies() {
  const store = await cookies();
  try {
    store.delete(ACCESS_COOKIE);
    store.delete(REFRESH_COOKIE);
    store.delete(ORG_COOKIE);
    store.delete(BOT_COOKIE);
  } catch {
    // Ignore read-only cookie contexts.
  }
}

export async function refreshAccessToken(): Promise<{ accessToken: string; refreshToken: string } | null> {
  const store = await cookies();
  const refreshToken = store.get(REFRESH_COOKIE)?.value ?? null;
  if (!refreshToken || !API_BASE) return null;
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) {
      await clearSessionCookies();
      return null;
    }
    const data = await response.json();
    await persistSessionTokens(data.access_token, data.refresh_token);
    return { accessToken: data.access_token, refreshToken: data.refresh_token };
  } catch {
    return null;
  }
}

async function fetchSessionUser(accessToken: string) {
  const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  return response;
}

async function keepScopeConsistent(store: Awaited<ReturnType<typeof cookies>>, resolvedOrgId: string | null, selectedOrgId: string | null) {
  if (resolvedOrgId && resolvedOrgId !== selectedOrgId) {
    try {
      store.set(ORG_COOKIE, resolvedOrgId, sessionScopeCookieOptions());
      store.delete(BOT_COOKIE);
    } catch {
      // Read-only cookie contexts are acceptable here.
    }
    return;
  }
  if (!resolvedOrgId && selectedOrgId) {
    try {
      store.delete(ORG_COOKIE);
      store.delete(BOT_COOKIE);
    } catch {
      // Ignore read-only cookie contexts.
    }
  }
}

export async function getSession(): Promise<{ user: SessionUser; organizationId: string | null } | null> {
  let accessToken = await getAccessToken();
  if (!API_BASE) return null;
  if (!accessToken) {
    const refreshed = await refreshAccessToken();
    if (!refreshed?.accessToken) return null;
    accessToken = refreshed.accessToken;
  }
  try {
    let response = await fetchSessionUser(accessToken);
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      if (!refreshed?.accessToken) return null;
      accessToken = refreshed.accessToken;
      response = await fetchSessionUser(accessToken);
    }
    if (!response.ok) return null;
    const user = normalizeSessionUser(await response.json());
    const store = await cookies();
    const selectedOrgId = store.get(ORG_COOKIE)?.value || null;
    const available = user.organizations || [];
    const resolvedOrgId = selectedOrgId && available.some((item) => item.id === selectedOrgId)
      ? selectedOrgId
      : available.length === 1
        ? available[0].id
        : null;
    await keepScopeConsistent(store, resolvedOrgId, selectedOrgId);
    return { user, organizationId: resolvedOrgId };
  } catch {
    return null;
  }
}

export async function requireSession(redirectTo = "/login") {
  const session = await getSession();
  if (!session) redirect(redirectTo);
  return session;
}

