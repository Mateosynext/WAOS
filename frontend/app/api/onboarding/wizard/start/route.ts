import { NextRequest } from "next/server";
import { readWizardJsonBody, wizardRouteResponse } from "../route-helpers";
import { startWizard } from "../../../../lib/data/wizard";

export async function POST(request: NextRequest) {
  return wizardRouteResponse(async () => startWizard(await readWizardJsonBody(request)), "No se pudo iniciar el wizard.");
}
