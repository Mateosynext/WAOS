import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../route-helpers";
import { getWizardVerticalProfile } from "../../../../lib/data/wizard";

export async function GET(request: NextRequest) {
  return wizardRouteResponse(() => getWizardVerticalProfile({
    organizationId: request.nextUrl.searchParams.get("organization_id"),
    botId: request.nextUrl.searchParams.get("bot_id"),
    verticalId: request.nextUrl.searchParams.get("vertical") || request.nextUrl.searchParams.get("vertical_id"),
    subvertical: request.nextUrl.searchParams.get("subvertical"),
  }), "No se pudo cargar el perfil vertical.");
}
