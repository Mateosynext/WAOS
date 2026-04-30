import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { ACCESS_COOKIE, BOT_COOKIE, ORG_COOKIE, REFRESH_COOKIE, sessionCookieOptions } from "./app/lib/auth/cookies";
import { verifyRequestSession } from "./app/lib/auth/edge-session";
import type { VerifiedSession } from "./app/lib/auth/edge-session";
import { describeRouteAccess, MIDDLEWARE_MATCHER } from "./app/lib/auth/route-policy";

function normalizeRole(role: string | null | undefined) {
  return String(role || "anonymous").toLowerCase();
}

function buildLoginRedirect(request: NextRequest) {
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  const nextTarget = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  if (nextTarget && nextTarget !== "/") url.searchParams.set("next", nextTarget);
  return url;
}

function syncSessionCookies(response: NextResponse, request: NextRequest, options: { accessToken?: string | null; refreshToken?: string | null; organizationId?: string | null; clearScope?: boolean } = {}) {
  const currentAccessToken = request.cookies.get(ACCESS_COOKIE)?.value ?? null;
  const currentRefreshToken = request.cookies.get(REFRESH_COOKIE)?.value ?? null;

  if (options.accessToken && options.accessToken !== currentAccessToken) {
    response.cookies.set(ACCESS_COOKIE, options.accessToken, sessionCookieOptions.access());
  }
  if (options.refreshToken && options.refreshToken !== currentRefreshToken) {
    response.cookies.set(REFRESH_COOKIE, options.refreshToken, sessionCookieOptions.refresh());
  }
  if (options.clearScope) {
    response.cookies.delete(ORG_COOKIE);
    response.cookies.delete(BOT_COOKIE);
  }
  if (typeof options.organizationId === "string" && options.organizationId.length) {
    response.cookies.set(ORG_COOKIE, options.organizationId, sessionCookieOptions.scope());
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const routeAccess = describeRouteAccess(pathname);

  if (routeAccess.isPublic && !routeAccess.isAuthPage) {
    return NextResponse.next();
  }

  let session: VerifiedSession | null = null;
  try {
    session = await verifyRequestSession(request);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("[middleware] session verification failed", error);
    if (routeAccess.isAuthPage) return NextResponse.next();
    const redirect = NextResponse.redirect(buildLoginRedirect(request));
    redirect.headers.set("x-waos-session-error", "verification_failed");
    redirect.cookies.delete(ACCESS_COOKIE);
    redirect.cookies.delete(REFRESH_COOKIE);
    redirect.cookies.delete(ORG_COOKIE);
    redirect.cookies.delete(BOT_COOKIE);
    return redirect;
  }

  if (routeAccess.isAuthPage) {
    if (!session) return NextResponse.next();
    const destination = new URL(
      session.user.organizations.length > 1 && !session.selectedOrganizationId
        ? "/organizations?source=login"
        : normalizeRole(session.user.global_role) === "client"
          ? "/client"
          : "/",
      request.url,
    );
    const response = NextResponse.redirect(destination);
    syncSessionCookies(response, request, {
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    });
    return response;
  }

  if (!session) {
    const redirect = NextResponse.redirect(buildLoginRedirect(request));
    redirect.cookies.delete(ACCESS_COOKIE);
    redirect.cookies.delete(REFRESH_COOKIE);
    redirect.cookies.delete(ORG_COOKIE);
    redirect.cookies.delete(BOT_COOKIE);
    return redirect;
  }

  const response = NextResponse.next();
  const selectedOrgId = session.selectedOrganizationId && session.organizationIds.includes(session.selectedOrganizationId)
    ? session.selectedOrganizationId
    : null;
  const resolvedOrganizationId = selectedOrgId || (session.organizationIds.length === 1 ? session.organizationIds[0] : null);

  if (selectedOrgId !== session.selectedOrganizationId) {
    syncSessionCookies(response, request, { clearScope: true });
    response.headers.set("x-waos-scope-repair", "invalid-selected-org-cleared");
  }
  syncSessionCookies(response, request, {
    accessToken: session.accessToken,
    refreshToken: session.refreshToken,
  });

  if (routeAccess.requiresOrganization) {
    if (!resolvedOrganizationId) {
      const destination = new URL("/organizations", request.url);
      destination.searchParams.set("source", "context-lock");
      destination.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
      const redirect = NextResponse.redirect(destination);
      syncSessionCookies(redirect, request, {
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        clearScope: true,
      });
      return redirect;
    }
    if (resolvedOrganizationId !== session.selectedOrganizationId) {
      syncSessionCookies(response, request, { organizationId: resolvedOrganizationId });
      response.cookies.delete(BOT_COOKIE);
      response.headers.set("x-waos-scope-repair", "organization-auto-selected");
    }
  }

  const allowedRoles = routeAccess.allowedRoles;
  if (allowedRoles && !allowedRoles.includes(normalizeRole(session.user.global_role))) {
    const destination = new URL("/", request.url);
    destination.searchParams.set("denied", pathname);
    const redirect = NextResponse.redirect(destination);
    syncSessionCookies(redirect, request, {
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      organizationId: resolvedOrganizationId,
    });
    return redirect;
  }

  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
