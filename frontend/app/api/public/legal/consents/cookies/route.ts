import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../../lib/env";

const API_BASE = getServerApiBase();

export async function POST(request: NextRequest) {
  if (!API_BASE) return NextResponse.json({ ok: false }, { status: 202 });
  try {
    const contentType = request.headers.get("content-type") || "application/json";
    const rawBody = await request.text();
    const response = await fetch(`${API_BASE}/api/public/legal/consents/cookies`, {
      method: "POST",
      headers: { "Content-Type": contentType },
      body: rawBody,
      cache: "no-store",
    });
    const text = await response.text().catch(() => "");
    if (!text) return NextResponse.json({ ok: response.ok }, { status: response.ok ? 202 : 202 });
    try {
      return NextResponse.json(JSON.parse(text), { status: response.ok ? 202 : 202 });
    } catch {
      return new NextResponse(text, { status: response.ok ? 202 : 202, headers: { "Content-Type": response.headers.get("content-type") || "text/plain; charset=utf-8" } });
    }
  } catch {
    return NextResponse.json({ ok: false }, { status: 202 });
  }
}
