import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../../../route-helpers";
import { saveWizardStep } from "../../../../../../lib/data/wizard";

type RouteContext = { params: Promise<{ wizardId: string; stepKey: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const { wizardId, stepKey } = await context.params;
  const body = await request.json().catch(() => ({}));
  const payload = body && typeof body === "object" && body.payload && typeof body.payload === "object" ? body.payload as Record<string, unknown> : {};
  const expectedRevision = body && typeof body === "object" && Number.isFinite(body.expected_revision) ? Number(body.expected_revision) : null;
  return wizardRouteResponse(() => saveWizardStep(wizardId, stepKey, payload, { expectedRevision }), "No se pudo guardar el paso del wizard.");
}
