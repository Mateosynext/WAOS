import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../lib/env";

const API_BASE = getServerApiBase();

export async function GET(request: NextRequest) {
  const providerId = request.nextUrl.searchParams.get("provider_id") || "";
  if (!API_BASE || !providerId) return NextResponse.redirect(new URL("/login?error=sso_unavailable", request.url));
  try {
    const response = await fetch(`${API_BASE}/api/v1/security/sso/${providerId}/start`, { method: "POST", cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    const authorizationUrl = typeof data?.authorization_url === "string" ? data.authorization_url : null;
    if (!response.ok || !authorizationUrl) return NextResponse.redirect(new URL("/login?error=sso_start_failed", request.url));
    return NextResponse.redirect(authorizationUrl);
  } catch {
    return NextResponse.redirect(new URL("/login?error=sso_start_failed", request.url));
  }
}
