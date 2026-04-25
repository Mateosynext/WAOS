import { NextRequest } from "next/server";
import { makeWizardValidationError, readWizardJsonBody, wizardPostOnlyResponse, wizardPostOptionsResponse, wizardRouteResponse } from "../route-helpers";
import { runWizardAiAutopilot } from "../../../../lib/data/wizard";
import { hasRequiredAutopilotScope, normalizeWizardAiAutopilotProxyPayload } from "@/features/bot-studio/services/wizardAutopilotContract";

export async function POST(request: NextRequest) {
  return wizardRouteResponse(async () => {
    const payload = normalizeWizardAiAutopilotProxyPayload(await readWizardJsonBody(request));
    if (!hasRequiredAutopilotScope(payload)) {
      throw makeWizardValidationError("organization_id es obligatorio para correr AI Autopilot.", [
        { loc: ["body", "organization_id"], msg: "organization_id es obligatorio.", type: "missing" },
      ]);
    }
    return runWizardAiAutopilot(payload);
  }, "No se pudo correr AI Autopilot end-to-end.");
}

export async function GET() {
  return wizardPostOnlyResponse("/api/onboarding/wizard/ai-autopilot");
}

export async function OPTIONS() {
  return wizardPostOptionsResponse();
}
