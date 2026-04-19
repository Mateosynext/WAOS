import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "../../../../lib/api";

function buildBlueprintPath(request: NextRequest) {
  const params = new URLSearchParams();
  const organizationId = request.nextUrl.searchParams.get("organization_id");
  const botId = request.nextUrl.searchParams.get("bot_id");
  const verticalId = request.nextUrl.searchParams.get("vertical_id") || request.nextUrl.searchParams.get("vertical");
  const subvertical = request.nextUrl.searchParams.get("subvertical");
  const primaryObjective = request.nextUrl.searchParams.get("primary_objective");

  if (organizationId) params.set("organization_id", organizationId);
  if (botId) params.set("bot_id", botId);
  if (verticalId) params.set("vertical_id", verticalId);
  if (subvertical) params.set("subvertical", subvertical);
  if (primaryObjective) params.set("primary_objective", primaryObjective);

  const query = params.toString();
  return `/api/v1/onboarding/wizard/blueprint${query ? `?${query}` : ""}`;
}

export async function GET(request: NextRequest) {
  try {
    const payload = await apiFetch<Record<string, unknown>>(buildBlueprintPath(request));
    return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo cargar el blueprint del wizard.";
    return NextResponse.json({ detail: message }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}
