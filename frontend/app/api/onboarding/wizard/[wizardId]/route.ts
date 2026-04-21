import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../route-helpers";
import { getWizardInstance } from "../../../../lib/data/wizard";

type RouteContext = { params: Promise<{ wizardId: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { wizardId } = await context.params;
  return wizardRouteResponse(() => getWizardInstance(wizardId), "No se pudo cargar el wizard.");
}
