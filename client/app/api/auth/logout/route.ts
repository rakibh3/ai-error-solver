import { cookies } from "next/headers"
import { NextResponse } from "next/server"
import { SESSION_COOKIE, backendUrl, isSameOrigin } from "@/lib/server/session"

export async function POST(request: Request) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request rejected" }, { status: 403 })
  }

  // Revoke the token server-side (bumps token_version) so a copied cookie
  // stops working too. The cookie is cleared either way: if the API is down or
  // the token is already invalid, the user still ends up signed out here.
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (token) {
    try {
      await fetch(`${backendUrl()}/api/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      })
    } catch {
      // Unreachable API: fall through and clear the cookie.
    }
  }

  const response = NextResponse.json({ status: "success" })
  response.cookies.delete(SESSION_COOKIE)
  return response
}
