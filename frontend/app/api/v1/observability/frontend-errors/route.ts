import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../lib/env";

const API_BASE = getServerApiBase();

async function forward(request: NextRequest) {
  if (!API_BASE) return NextResponse.json({ ok: false }, { status: 202 });
  try {
    const contentType = request.headers.get("content-type") || "application/json";
    const rawBody = await request.text();
    const response = await fetch(`${API_BASE}/api/v1/observability/frontend-errors`, {
      method: "POST",
      headers: { "Content-Type": contentType },
      body: rawBody,
      cache: "no-store",
    });
    if (!response.ok) {
      return NextResponse.json({ ok: false }, { status: 202 });
    }
    const text = await response.text().catch(() => "");
    if (!text) return NextResponse.json({ ok: true }, { status: 202 });
    try {
      return NextResponse.json(JSON.parse(text), { status: 202 });
    } catch {
      return new NextResponse(text, { status: 202, headers: { "Content-Type": response.headers.get("content-type") || "text/plain; charset=utf-8" } });
    }
  } catch {
    return NextResponse.json({ ok: false }, { status: 202 });
  }
}

export async function POST(request: NextRequest) {
  return forward(request);
}
