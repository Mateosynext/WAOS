import type { NextRequest } from "next/server";
import { normalizeSessionUser, type SessionUser } from "../contracts/auth.ts";
import { getServerApiBase } from "../env.ts";
import { ACCESS_COOKIE, ORG_COOKIE, REFRESH_COOKIE } from "./cookies.ts";

const API_BASE = getServerApiBase();

type JwtClaims = {
  sub?: string;
  role?: string;
  type?: string;
  sid?: string;
  exp?: number;
  iat?: number;
  nbf?: number;
};

export type VerifiedSession = {
  accessToken: string;
  refreshToken: string | null;
  user: SessionUser;
  organizationIds: string[];
  selectedOrganizationId: string | null;
};

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return atob(padded);
}

export function decodeAccessTokenClaims(token: string | null | undefined): JwtClaims | null {
  const raw = String(token || "").trim();
  if (!raw) return null;
  const parts = raw.split(".");
  if (parts.length < 2) return null;
  try {
    return JSON.parse(decodeBase64Url(parts[1])) as JwtClaims;
  } catch {
    return null;
  }
}

export function isExpiredJwt(claims: JwtClaims | null, nowSeconds = Math.floor(Date.now() / 1000)) {
  if (!claims?.exp || !Number.isFinite(claims.exp)) return true;
  return claims.exp <= nowSeconds;
}

async function refreshSession(refreshToken: string) {
  if (!API_BASE) return null;
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) return null;
    const payload = await response.json().catch(() => null);
    if (typeof payload?.access_token !== "string" || typeof payload?.refresh_token !== "string") return null;
    return { accessToken: payload.access_token, refreshToken: payload.refresh_token };
  } catch {
    return null;
  }
}

async function fetchSessionUser(accessToken: string, selectedOrganizationId: string | null) {
  if (!API_BASE) return null;
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  if (selectedOrganizationId) {
    headers.set("x-waos-org-id", selectedOrganizationId);
    headers.set("x-organization-id", selectedOrganizationId);
  }
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
      method: "GET",
      headers,
      cache: "no-store",
    });
    if (!response.ok) return null;
    return normalizeSessionUser(await response.json());
  } catch {
    return null;
  }
}

export async function verifyRequestSession(request: NextRequest): Promise<VerifiedSession | null> {
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value ?? null;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value ?? null;
  const selectedOrganizationId = request.cookies.get(ORG_COOKIE)?.value ?? null;
  if (!accessToken && !refreshToken) return null;

  let activeAccessToken = accessToken || "";
  let activeRefreshToken = refreshToken;
  const initialClaims = accessToken ? decodeAccessTokenClaims(activeAccessToken) : null;

  if ((!accessToken || !initialClaims || initialClaims.type !== "access" || isExpiredJwt(initialClaims)) && refreshToken) {
    const refreshed = await refreshSession(refreshToken);
    if (!refreshed) return null;
    activeAccessToken = refreshed.accessToken;
    activeRefreshToken = refreshed.refreshToken;
  } else if (!initialClaims || initialClaims.type !== "access") {
    return null;
  } else if (isExpiredJwt(initialClaims)) {
    return null;
  }

  let user = await fetchSessionUser(activeAccessToken, selectedOrganizationId);
  if (!user && activeRefreshToken) {
    const refreshed = await refreshSession(activeRefreshToken);
    if (!refreshed) return null;
    activeAccessToken = refreshed.accessToken;
    activeRefreshToken = refreshed.refreshToken;
    user = await fetchSessionUser(activeAccessToken, selectedOrganizationId);
  }
  if (!user) return null;

  const organizationIds = (user.organizations || []).map((item) => item.id).filter(Boolean);
  return {
    accessToken: activeAccessToken,
    refreshToken: activeRefreshToken,
    user,
    organizationIds,
    selectedOrganizationId,
  };
}
