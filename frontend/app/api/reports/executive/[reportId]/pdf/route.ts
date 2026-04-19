import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase } from "../../../../../lib/env";
import { ACCESS_COOKIE } from "../../../../../lib/session";

const API_BASE = getServerApiBase();

export async function GET(request: NextRequest, context: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await context.params;
  const access = request.cookies.get(ACCESS_COOKIE)?.value || "";
  if (!API_BASE || !access || !reportId) return new NextResponse("Unauthorized", { status: 401 });
  try {
    const response = await fetch(`${API_BASE}/api/v1/reports/executive/${reportId}/pdf`, { headers: { Authorization: `Bearer ${access}` }, cache: "no-store" });
    if (!response.ok) {
      const text = await response.text().catch(() => "No se pudo generar el PDF.");
      return new NextResponse(text || "No se pudo generar el PDF.", { status: response.status || 502, headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
    const bytes = await response.arrayBuffer();
    return new NextResponse(bytes, { headers: { "Content-Type": "application/pdf", "Content-Disposition": response.headers.get("content-disposition") || `attachment; filename=waos-report-${reportId}.pdf` } });
  } catch {
    return new NextResponse("No se pudo generar el PDF.", { status: 502, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
}
