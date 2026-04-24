import "server-only";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import type { SessionUser } from "./contracts/auth";
import { getServerApiBase } from "./env";
import { requestSessionRefresh } from "./auth/refresh";
import { fetchSessionUserFromApi, resolveSessionOrganizationId } from "./auth/shared-session";
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
  if (!refreshToken) return null;
  const refreshed = await requestSessionRefresh(refreshToken, API_BASE);
  if (!refreshed) {
    await clearSessionCookies();
    return null;
  }
  await persistSessionTokens(refreshed.accessToken, refreshed.refreshToken);
  return { accessToken: refreshed.accessToken, refreshToken: refreshed.refreshToken };
}

async function fetchSessionUser(accessToken: string) {
  return fetchSessionUserFromApi(API_BASE, accessToken);
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
    let user = await fetchSessionUser(accessToken);
    if (!user) {
      const refreshed = await refreshAccessToken();
      if (!refreshed?.accessToken) return null;
      accessToken = refreshed.accessToken;
      user = await fetchSessionUser(accessToken);
    }
    if (!user) return null;
    const store = await cookies();
    const selectedOrgId = store.get(ORG_COOKIE)?.value || null;
    const resolvedOrgId = resolveSessionOrganizationId(user, selectedOrgId);
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

