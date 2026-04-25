import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../route-helpers";
import { runWizardAiAutopilot } from "../../../../lib/data/wizard";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return wizardRouteResponse(() => runWizardAiAutopilot({
    organizationId: String(body?.organization_id || body?.organizationId || ""),
    botId: body?.bot_id || body?.botId || null,
    verticalId: body?.vertical_id || body?.verticalId || null,
    subvertical: body?.subvertical || null,
    primaryObjective: body?.primary_objective || body?.primaryObjective || null,
    userDescription: String(body?.user_description || body?.userDescription || ""),
    intensity: body?.intensity || "aggressive",
    existingAnswers: body?.existing_answers || body?.existingAnswers || {},
    maxAutofixRounds: Number(body?.max_autofix_rounds || body?.maxAutofixRounds || 2),
    autoApply: Boolean(body?.auto_apply || body?.autoApply || false),
  }), "No se pudo correr AI Autopilot end-to-end.");
}
