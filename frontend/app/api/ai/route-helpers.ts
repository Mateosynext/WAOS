import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, refreshAccessToken } from "@/app/lib/session";
import { getServerApiBase } from "@/app/lib/env";

export async function getBearerToken() {
  const store = await cookies();
  return store.get(ACCESS_COOKIE)?.value || (await refreshAccessToken())?.accessToken || "";
}

export async function proxyJson(request: Request, backendPath: string, method = request.method) {
  const base = getServerApiBase();
  if (!base) return NextResponse.json({ detail: { message: "Backend API base missing", code: "missing_api_base" } }, { status: 500 });
  const token = await getBearerToken();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();
  const contentType = request.headers.get("content-type") || "application/json";
  const url = new URL(request.url);
  const upstreamPath = `${backendPath}${url.search || ""}`;
  try {
    const response = await fetch(`${base}${upstreamPath}`, {
      method,
      body,
      headers: {
        "Content-Type": contentType,
        "Accept": request.headers.get("accept") || "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    });
    const text = await response.text();
    return new NextResponse(text || "{}", {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend proxy failed";
    return NextResponse.json({ detail: { code: "backend_unreachable", message } }, { status: 502 });
  }
}
