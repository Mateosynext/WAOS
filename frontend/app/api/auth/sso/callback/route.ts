import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../lib/env";
import { ACCESS_COOKIE, ORG_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "../../../../lib/session";

const API_BASE = getServerApiBase();

export async function GET(request: NextRequest) {
  const state = request.nextUrl.searchParams.get("state") || "";
  const code = request.nextUrl.searchParams.get("code") || "";
  if (!API_BASE || !state || !code) return NextResponse.redirect(new URL("/login?error=sso_callback_invalid", request.url));
  const response = await fetch(`${API_BASE}/api/v1/security/sso/callback?state=${encodeURIComponent(state)}&code=${encodeURIComponent(code)}`, { cache: "no-store" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data?.access_token || !data?.refresh_token) return NextResponse.redirect(new URL("/login?error=sso_callback_failed", request.url));
  const next = NextResponse.redirect(new URL(data?.user?.global_role === "client" ? "/client" : "/", request.url));
  next.cookies.set(ACCESS_COOKIE, data.access_token, sessionCookieOptions.access());
  next.cookies.set(REFRESH_COOKIE, data.refresh_token, sessionCookieOptions.refresh());
  const orgs = data?.user?.organizations || [];
  if (orgs.length === 1 && orgs[0]?.id) next.cookies.set(ORG_COOKIE, orgs[0].id, sessionCookieOptions.scope());
  return next;
}
