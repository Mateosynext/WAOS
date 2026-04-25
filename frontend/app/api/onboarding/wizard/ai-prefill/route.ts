import { NextRequest } from "next/server";
import { wizardPostOnlyResponse, wizardPostOptionsResponse, wizardRouteResponse } from "../route-helpers";
import { generateWizardAiPrefill } from "../../../../lib/data/wizard";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return wizardRouteResponse(() => generateWizardAiPrefill({
    organizationId: String(body?.organization_id || body?.organizationId || ""),
    botId: body?.bot_id || body?.botId || null,
    verticalId: body?.vertical_id || body?.verticalId || null,
    subvertical: body?.subvertical || null,
    primaryObjective: body?.primary_objective || body?.primaryObjective || null,
    userDescription: String(body?.user_description || body?.userDescription || ""),
    intensity: body?.intensity || "balanced",
    existingAnswers: body?.existing_answers || body?.existingAnswers || {},
  }), "No se pudo generar el setup con IA.");
}


export async function GET() {
  return wizardPostOnlyResponse("/api/onboarding/wizard/ai-prefill");
}

export async function OPTIONS() {
  return wizardPostOptionsResponse();
}
