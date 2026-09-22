import { NextResponse } from "next/server"
import {
  SESSION_COOKIE,
  backendUrl,
  clientIp,
  isSameOrigin,
  sessionCookieOptions,
} from "@/lib/server/session"

// Exchanges credentials for a JWT at POST /api/v1/auth/login and stores the
// token in an httpOnly cookie. Only the user object is returned to the browser.
export async function POST(request: Request) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request rejected" }, { status: 403 })
  }

  const body = await request.text()
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  const ip = clientIp(request)
  if (ip) headers["X-Forwarded-For"] = ip

  let upstream: Response
  try {
    upstream = await fetch(`${backendUrl()}/api/v1/auth/login`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
    })
  } catch {
    return NextResponse.json(
      { detail: "The API server is unreachable. Please try again shortly." },
      { status: 502 },
    )
  }

  const data = await upstream.json().catch(() => null)
  if (!upstream.ok) {
    return NextResponse.json(data ?? { detail: "Sign in failed" }, { status: upstream.status })
  }

  const token: string | undefined = data?.token?.access_token
  if (!token) {
    return NextResponse.json({ detail: "Malformed login response" }, { status: 502 })
  }

  const response = NextResponse.json({ user: data.user })
  response.cookies.set(SESSION_COOKIE, token, sessionCookieOptions(request))
  return response
}
