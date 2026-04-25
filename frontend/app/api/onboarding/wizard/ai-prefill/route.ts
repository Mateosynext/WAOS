import { NextRequest } from "next/server";
import { makeWizardValidationError, readWizardJsonBody, wizardPostOnlyResponse, wizardPostOptionsResponse, wizardRouteResponse } from "../route-helpers";
import { generateWizardAiPrefill } from "../../../../lib/data/wizard";
import { hasRequiredAutopilotScope, normalizeWizardAiProxyPayload } from "@/features/bot-studio/services/wizardAutopilotContract";

export async function POST(request: NextRequest) {
  return wizardRouteResponse(async () => {
    const payload = normalizeWizardAiProxyPayload(await readWizardJsonBody(request), "balanced");
    if (!hasRequiredAutopilotScope(payload)) {
      throw makeWizardValidationError("organization_id es obligatorio para generar setup con IA.", [
        { loc: ["body", "organization_id"], msg: "organization_id es obligatorio.", type: "missing" },
      ]);
    }
    return generateWizardAiPrefill(payload);
  }, "No se pudo generar el setup con IA.");
}

export async function GET() {
  return wizardPostOnlyResponse("/api/onboarding/wizard/ai-prefill");
}

export async function OPTIONS() {
  return wizardPostOptionsResponse();
}
