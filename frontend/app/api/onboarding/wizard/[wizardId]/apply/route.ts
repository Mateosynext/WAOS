import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../../route-helpers";
import { applyWizard } from "../../../../../lib/data/wizard";

type RouteContext = { params: Promise<{ wizardId: string }> };

export async function POST(_request: NextRequest, context: RouteContext) {
  const { wizardId } = await context.params;
  return wizardRouteResponse(() => applyWizard(wizardId), "No se pudo aplicar el wizard.");
}
