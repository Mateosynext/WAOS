import { NextResponse } from "next/server";
import { apiFetch } from "../../../../lib/api";
import { normalizeCollection, normalizeVerticalProfile } from "../../../../lib/contracts";

export async function GET() {
  try {
    const payload = await apiFetch<unknown>("/api/v1/onboarding/wizard/verticals");
    return NextResponse.json(normalizeCollection(payload, normalizeVerticalProfile), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "No se pudo cargar el catalogo del wizard.";
    return NextResponse.json({ detail: message }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}
