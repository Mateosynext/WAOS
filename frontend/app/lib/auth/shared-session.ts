import { normalizeSessionUser, type SessionUser } from "../contracts/auth";

export const AUTH_ME_PATH = "/api/v1/auth/me";
export const AUTH_REFRESH_PATH = "/api/v1/auth/refresh";

export function buildSessionUserHeaders(accessToken: string, selectedOrganizationId: string | null = null) {
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  if (selectedOrganizationId) {
    headers.set("x-waos-org-id", selectedOrganizationId);
    headers.set("x-organization-id", selectedOrganizationId);
  }
  return headers;
}

export function resolveSessionOrganizationId(user: SessionUser, selectedOrganizationId: string | null) {
  const available = user.organizations || [];
  if (selectedOrganizationId && available.some((item) => item.id === selectedOrganizationId)) {
    return selectedOrganizationId;
  }
  if (available.length === 1) {
    return available[0]?.id || null;
  }
  return null;
}

export async function fetchSessionUserFromApi(apiBase: string | null, accessToken: string, selectedOrganizationId: string | null = null): Promise<SessionUser | null> {
  if (!apiBase || !accessToken) return null;
  try {
    const response = await fetch(`${apiBase}${AUTH_ME_PATH}`, {
      method: "GET",
      headers: buildSessionUserHeaders(accessToken, selectedOrganizationId),
      cache: "no-store",
    });
    if (!response.ok) return null;
    return normalizeSessionUser(await response.json());
  } catch {
    return null;
  }
}
