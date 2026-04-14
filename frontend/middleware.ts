import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/_next") || pathname.startsWith("/login") || pathname === "/favicon.ico") {
    return NextResponse.next();
  }
  const token = request.cookies.get("waos_access_token")?.value;
  if (!token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api).*)"],
};
