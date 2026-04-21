export const ACCESS_COOKIE = "waos_access_token";
export const REFRESH_COOKIE = "waos_refresh_token";
export const ORG_COOKIE = "waos_org_id";
export const BOT_COOKIE = "waos_bot_id";
export const CSRF_COOKIE = "waos_csrf_token";

const secureCookies = process.env.NODE_ENV === "production" || process.env.SECURE_COOKIES === "true";

export function accessCookieOptions() {
  return { httpOnly: true as const, sameSite: "lax" as const, secure: secureCookies, path: "/", maxAge: 60 * 60 };
}

export function refreshCookieOptions() {
  return { httpOnly: true as const, sameSite: "strict" as const, secure: secureCookies, path: "/", maxAge: 60 * 60 * 12 };
}

export function sessionScopeCookieOptions() {
  return { httpOnly: true as const, sameSite: "lax" as const, secure: secureCookies, path: "/" };
}

export const sessionCookieOptions = {
  access: accessCookieOptions,
  refresh: refreshCookieOptions,
  scope: sessionScopeCookieOptions,
};
