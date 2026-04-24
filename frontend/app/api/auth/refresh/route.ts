import { NextRequest, NextResponse } from "next/server";
import { ACCESS_COOKIE, ORG_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "../../../lib/auth/cookies";
import { requestSessionRefresh } from "../../../lib/auth/refresh";

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value || null;
  if (!refreshToken) {
    return NextResponse.json({ detail: "Missing refresh token" }, { status: 401 });
  }
  const refreshed = await requestSessionRefresh(refreshToken);
  if (!refreshed) {
    const failed = NextResponse.json({ detail: "Refresh failed" }, { status: 401 });
    failed.cookies.delete(ACCESS_COOKIE);
    failed.cookies.delete(REFRESH_COOKIE);
    return failed;
  }
  const ok = NextResponse.json({ access_token: refreshed.accessToken, refresh_token: refreshed.refreshToken, session: refreshed.session ?? null });
  ok.cookies.set(ACCESS_COOKIE, refreshed.accessToken, sessionCookieOptions.access());
  ok.cookies.set(REFRESH_COOKIE, refreshed.refreshToken, sessionCookieOptions.refresh());
  return ok;
}

