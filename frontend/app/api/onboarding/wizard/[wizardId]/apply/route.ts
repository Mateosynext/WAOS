import { NextRequest } from "next/server";
import { readWizardJsonBody, wizardRouteResponse } from "../../route-helpers";
import { applyWizard } from "../../../../../lib/data/wizard";

type RouteContext = { params: Promise<{ wizardId: string }> };

function isExplicitConfirm(value: unknown) {
  if (value === true) return true;
  if (typeof value === "string") return value.trim().toLowerCase() === "true";
  if (typeof value === "number") return value === 1;
  return false;
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { wizardId } = await context.params;
  return wizardRouteResponse(async () => {
    const body = await readWizardJsonBody(request);
    if (!isExplicitConfirm(body.confirm)) {
      const error = new Error("explicit_confirmation_required") as Error & { status?: number; code?: string };
      error.status = 409;
      error.code = "explicit_confirmation_required";
      throw error;
    }
    return applyWizard(wizardId);
  }, "No se pudo aplicar el wizard.");
}
