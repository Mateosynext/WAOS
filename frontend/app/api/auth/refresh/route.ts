import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../lib/env";
import { ACCESS_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "../../../lib/session";

const API_BASE = getServerApiBase();

export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value || null;
  if (!refreshToken || !API_BASE) {
    return NextResponse.json({ detail: "Missing refresh token" }, { status: 401 });
  }
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) {
      const failed = NextResponse.json({ detail: "Refresh failed" }, { status: 401 });
      failed.cookies.delete(ACCESS_COOKIE);
      failed.cookies.delete(REFRESH_COOKIE);
      return failed;
    }
    const data = await response.json();
    const ok = NextResponse.json({ access_token: data.access_token, refresh_token: data.refresh_token, session: data.session });
    ok.cookies.set(ACCESS_COOKIE, data.access_token, sessionCookieOptions.access());
    ok.cookies.set(REFRESH_COOKIE, data.refresh_token, sessionCookieOptions.refresh());
    return ok;
  } catch {
    return NextResponse.json({ detail: "Refresh failed" }, { status: 401 });
  }
}
