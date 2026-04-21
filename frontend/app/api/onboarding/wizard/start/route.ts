import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../route-helpers";
import { startWizard } from "../../../../lib/data/wizard";

export async function POST(request: NextRequest) {
  return wizardRouteResponse(async () => startWizard(await request.json().catch(() => ({}))), "No se pudo iniciar el wizard.");
}
