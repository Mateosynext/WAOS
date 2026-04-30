import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../lib/env";

const API_BASE = getServerApiBase();
const TELEMETRY_TOKEN = process.env.FRONTEND_TELEMETRY_PUBLIC_TOKEN || process.env.NEXT_PUBLIC_FRONTEND_TELEMETRY_TOKEN || "";
const MAX_TELEMETRY_BODY_BYTES = 8192;

async function forward(request: NextRequest) {
  if (!API_BASE) return NextResponse.json({ ok: false }, { status: 202 });
  try {
    const contentLength = Number(request.headers.get("content-length") || "0");
    if (Number.isFinite(contentLength) && contentLength > MAX_TELEMETRY_BODY_BYTES) {
      return NextResponse.json({ ok: false, code: "frontend_telemetry_payload_too_large" }, { status: 413 });
    }
    const contentType = request.headers.get("content-type") || "application/json";
    const rawBody = await request.text();
    if (rawBody.length > MAX_TELEMETRY_BODY_BYTES) {
      return NextResponse.json({ ok: false, code: "frontend_telemetry_payload_too_large" }, { status: 413 });
    }
    const headers: Record<string, string> = { "Content-Type": contentType };
    const origin = request.headers.get("origin");
    const userAgent = request.headers.get("user-agent");
    if (origin) headers.Origin = origin;
    if (userAgent) headers["X-WAOS-Client-User-Agent"] = userAgent.slice(0, 240);
    if (TELEMETRY_TOKEN) headers["X-WAOS-Frontend-Telemetry-Token"] = TELEMETRY_TOKEN;
    const response = await fetch(`${API_BASE}/api/v1/observability/frontend-errors`, {
      method: "POST",
      headers,
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
