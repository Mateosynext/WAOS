import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "../../../../lib/api";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const payload = await apiFetch<Record<string, unknown>>("/api/v1/onboarding/wizard/start", {
      method: "POST",
      body: JSON.stringify(body || {}),
    });
    return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo iniciar el wizard.";
    return NextResponse.json({ detail: message }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}
