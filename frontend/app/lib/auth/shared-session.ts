import { normalizeSessionUser, type SessionUser } from "../contracts/auth";

export const AUTH_ME_PATH = "/api/v1/auth/me";
export const AUTH_REFRESH_PATH = "/api/v1/auth/refresh";

export class SessionFetchError extends Error {
  status: number | null;
  code: string;
  constructor(message: string, options: { status?: number | null; code?: string } = {}) {
    super(message);
    this.name = "SessionFetchError";
    this.status = options.status ?? null;
    this.code = options.code || "session_fetch_failed";
  }
}

function logSessionFetchFailure(error: unknown) {
  // eslint-disable-next-line no-console
  console.error("[session] failed to resolve /auth/me", error);
}

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
    if (response.status === 401 || response.status === 403) return null;
    if (!response.ok) {
      throw new SessionFetchError(`auth_me_failed:${response.status}`, { status: response.status, code: "auth_me_failed" });
    }
    return normalizeSessionUser(await response.json());
  } catch (error) {
    logSessionFetchFailure(error);
    if (error instanceof SessionFetchError) throw error;
    throw new SessionFetchError(error instanceof Error ? error.message : "auth_me_network_error", { code: "auth_me_network_error" });
  }
}
