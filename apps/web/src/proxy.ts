import { NextResponse, type NextRequest } from "next/server";

/**
 * Signed-out visitors to an app page go to /sign-in?next=<path>. This only checks that a session
 * cookie is present (an optimistic check); the API checks the session itself on every call, and
 * a 401 there also sends the page to sign-in (components/app/RoleShell).
 *
 * While the "Act as" stand-in is on (development, or NEXT_PUBLIC_ALLOW_ROLE_SWITCHER=true) pages
 * open without a session, as the API serves the stand-in user.
 */
const SESSION_COOKIE = "pratyay_session";
const STAND_IN =
  process.env.NEXT_PUBLIC_APP_ENV === "development" || process.env.NEXT_PUBLIC_ALLOW_ROLE_SWITCHER === "true";

export function proxy(request: NextRequest) {
  if (STAND_IN || request.cookies.get(SESSION_COOKIE)?.value) return NextResponse.next();
  const url = request.nextUrl.clone();
  const next = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  url.pathname = "/sign-in";
  url.search = `?next=${encodeURIComponent(next)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/auditor/:path*",
    "/borrower/:path*",
    "/checker/:path*",
    "/crypto-lab/:path*",
    "/maker/:path*",
    "/officer/:path*",
    "/rules/:path*",
  ],
};
