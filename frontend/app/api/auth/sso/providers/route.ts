import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../lib/env";

const API_BASE = getServerApiBase();

export async function GET(request: NextRequest) {
  if (!API_BASE) return NextResponse.json([], { status: 200 });
  const email = request.nextUrl.searchParams.get("email") || "";
  const organizationSlug = request.nextUrl.searchParams.get("organization_slug") || "";
  const query = new URLSearchParams();
  if (email) query.set("email", email);
  if (organizationSlug) query.set("organization_slug", organizationSlug);
  try {
    const response = await fetch(`${API_BASE}/api/public/sso/providers?${query.toString()}`, { cache: "no-store" });
    const data = await response.json().catch(() => []);
    return NextResponse.json(Array.isArray(data) ? data : [], { status: response.ok ? 200 : 200 });
  } catch {
    return NextResponse.json([], { status: 200 });
  }
}
