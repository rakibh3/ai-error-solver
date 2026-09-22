import { NextResponse, type NextRequest } from "next/server"
import { cookies } from "next/headers"
import { SESSION_COOKIE, backendUrl, clientIp, isSameOrigin } from "@/lib/server/session"

// Backend-for-frontend proxy: /api/backend/<path> -> BACKEND_URL/<path>.
//
// Why a proxy rather than calling FastAPI from the browser:
//  - the JWT stays in an httpOnly cookie, out of reach of injected scripts;
//  - the API has no CORS middleware, so same-origin avoids it entirely.

export const dynamic = "force-dynamic"

type Ctx = { params: Promise<{ path?: string[] }> }

// Only the public API surface is reachable; /docs, /redoc etc. are not proxied.
function isAllowed(segments: string[]): boolean {
  if (segments.some((s) => s === "" || s === "." || s === "..")) return false
  if (segments.length === 0) return true // GET / liveness
  return segments[0] === "api" && segments[1] === "v1" && segments.length > 2
}

const FORWARDED_REQUEST_HEADERS = ["accept", "content-type"]
const FORWARDED_RESPONSE_HEADERS = ["content-type", "retry-after", "www-authenticate"]

async function proxy(request: NextRequest, ctx: Ctx) {
  const { path = [] } = await ctx.params
  if (!isAllowed(path)) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 })
  }
  if (request.method !== "GET" && !isSameOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request rejected" }, { status: 403 })
  }

  const target = new URL(`${backendUrl()}/${path.map(encodeURIComponent).join("/")}`)
  target.search = request.nextUrl.search

  const headers = new Headers()
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name)
    if (value) headers.set(name, value)
  }

  // Set, not appended: the API trusts this header only from this server.
  const ip = clientIp(request)
  if (ip) headers.set("x-forwarded-for", ip)

  const cookieStore = await cookies()
  const token = cookieStore.get(SESSION_COOKIE)?.value
  if (token) headers.set("authorization", `Bearer ${token}`)

  const hasBody = request.method !== "GET" && request.method !== "HEAD"

  let upstream: Response
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? request.body : undefined,
      // Required by Node's fetch to stream a request body (multipart uploads).
      ...(hasBody ? { duplex: "half" } : {}),
      cache: "no-store",
      redirect: "manual",
    } as RequestInit)
  } catch {
    return NextResponse.json(
      { detail: "The API server is unreachable. Please try again shortly." },
      { status: 502 },
    )
  }

  const responseHeaders = new Headers()
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name)
    if (value) responseHeaders.set(name, value)
  }

  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  })
  // A rejected token is dead for good (expired, or the account is gone).
  if (upstream.status === 401 && token) response.cookies.delete(SESSION_COOKIE)
  return response
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
}
