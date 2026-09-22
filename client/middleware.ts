import { NextResponse, type NextRequest } from "next/server"

// Keep in sync with lib/server/session.ts (not importable from the edge runtime).
const SESSION_COOKIE = "en_session"

// Cookie presence is only a routing hint. The API validates the token on every
// request, and the client shell re-checks the role via GET /auth/me.
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl
  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE)?.value)
  const isAppRoute = pathname.startsWith("/dashboard") || pathname.startsWith("/admin")
  const isAuthRoute = pathname === "/login" || pathname === "/register"

  if (isAppRoute && !hasSession) {
    const url = new URL("/login", request.url)
    url.searchParams.set("next", `${pathname}${search}`)
    return NextResponse.redirect(url)
  }
  if (isAuthRoute && hasSession) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*", "/login", "/register"],
}
