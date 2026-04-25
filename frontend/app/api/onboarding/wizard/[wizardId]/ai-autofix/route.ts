import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../../route-helpers";
import { autofixWizardWithAi } from "../../../../../lib/data/wizard";

type RouteContext = { params: Promise<{ wizardId: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const { wizardId } = await context.params;
  const body = await request.json().catch(() => ({}));
  return wizardRouteResponse(() => autofixWizardWithAi(wizardId, String(body?.user_description || body?.userDescription || "")), "No se pudo arreglar el wizard con IA.");
}
