import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../route-helpers";
import { getWizardBlueprint } from "../../../../lib/data/wizard";

export async function GET(request: NextRequest) {
  return wizardRouteResponse(() => getWizardBlueprint({
    organizationId: request.nextUrl.searchParams.get("organization_id") || "",
    botId: request.nextUrl.searchParams.get("bot_id"),
    verticalId: request.nextUrl.searchParams.get("vertical_id") || request.nextUrl.searchParams.get("vertical") || "",
    subvertical: request.nextUrl.searchParams.get("subvertical"),
    primaryObjective: request.nextUrl.searchParams.get("primary_objective"),
  }), "No se pudo cargar el blueprint del wizard.");
}
