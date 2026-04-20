import { NextRequest, NextResponse } from "next/server";
import { getVerticalProfile } from "../../../../lib/waos";

export async function GET(request: NextRequest) {
  const organizationId = request.nextUrl.searchParams.get("organization_id") || undefined;
  const botId = request.nextUrl.searchParams.get("bot_id") || undefined;
  const vertical = request.nextUrl.searchParams.get("vertical") || undefined;
  const subvertical = request.nextUrl.searchParams.get("subvertical") || undefined;
  const profile = await getVerticalProfile(vertical, botId, subvertical, organizationId);
  return NextResponse.json(profile, { headers: { "Cache-Control": "no-store" } });
}
