import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "../../../../lib/api";
import { normalizeVerticalProfile } from "../../../../lib/contracts";

function buildVerticalProfilePath(request: NextRequest) {
  const params = new URLSearchParams();
  for (const key of ["organization_id", "bot_id", "vertical", "subvertical"]) {
    const value = request.nextUrl.searchParams.get(key);
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return `/api/v1/verticals/profile${query ? `?${query}` : ""}`;
}

export async function GET(request: NextRequest) {
  try {
    const payload = await apiFetch<unknown>(buildVerticalProfilePath(request));
    return NextResponse.json(normalizeVerticalProfile(payload), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo cargar el perfil vertical.";
    return NextResponse.json({ detail: message }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}
