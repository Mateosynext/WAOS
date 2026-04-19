import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "../../../../../../lib/api";

type RouteContext = { params: Promise<{ wizardId: string; stepKey: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  try {
    const { wizardId, stepKey } = await context.params;
    const body = await request.json();
    const payload = await apiFetch<Record<string, unknown>>(`/api/v1/onboarding/wizard/${encodeURIComponent(wizardId)}/steps/${encodeURIComponent(stepKey)}`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    });
    return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo guardar el paso del wizard.";
    return NextResponse.json({ detail: message }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}
