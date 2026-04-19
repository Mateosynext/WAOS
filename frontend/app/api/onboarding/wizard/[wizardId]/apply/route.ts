import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "../../../../../lib/api";

type RouteContext = { params: Promise<{ wizardId: string }> };

export async function POST(_request: NextRequest, context: RouteContext) {
  try {
    const { wizardId } = await context.params;
    const payload = await apiFetch<Record<string, unknown>>(`/api/v1/onboarding/wizard/${encodeURIComponent(wizardId)}/apply`, {
      method: "POST",
    });
    return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo aplicar el wizard.";
    return NextResponse.json({ detail: message }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}
