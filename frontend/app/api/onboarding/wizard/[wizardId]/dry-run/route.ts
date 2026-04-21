import { NextRequest } from "next/server";
import { wizardRouteResponse } from "../../route-helpers";
import { runWizardDryRun } from "../../../../../lib/data/wizard";

type RouteContext = { params: Promise<{ wizardId: string }> };

export async function POST(_request: NextRequest, context: RouteContext) {
  const { wizardId } = await context.params;
  return wizardRouteResponse(() => runWizardDryRun(wizardId), "No se pudo ejecutar el dry run.");
}
