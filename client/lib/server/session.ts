import "server-only"

// Server-only: the FastAPI origin and the session cookie contract. Imported by
// the BFF route handlers; middleware.ts duplicates SESSION_COOKIE because the
// edge runtime cannot import a `server-only` module.

export const SESSION_COOKIE = "en_session"

// Matches ACCESS_TOKEN_EXPIRE_MINUTES on the server (30 days).
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

export function backendUrl(): string {
  return (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "")
}

/**
 * Whether the session cookie gets the `Secure` flag.
 *
 * Decided by how the request actually arrived, not by NODE_ENV: a production
 * build served over plain HTTP (LAN IP, staging without TLS) would otherwise
 * set a Secure cookie the browser never sends back, and every login would
 * silently bounce to /login. Behind a TLS-terminating proxy, X-Forwarded-Proto
 * carries the original scheme. SESSION_COOKIE_SECURE=true|false overrides.
 */
function isSecureRequest(request: Request): boolean {
  const override = process.env.SESSION_COOKIE_SECURE?.trim().toLowerCase()
  if (override === "true") return true
  if (override === "false") return false
  const forwarded = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim().toLowerCase()
  if (forwarded) return forwarded === "https"
  return new URL(request.url).protocol === "https:"
}

export function sessionCookieOptions(request: Request) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: isSecureRequest(request),
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  }
}

/**
 * Reject cross-site state-changing requests. SameSite=Lax already withholds the
 * cookie from cross-site POSTs; this is a second, explicit check.
 */
export function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin")
  if (!origin) return true // same-origin fetches from older browsers omit it
  try {
    return new URL(origin).host === request.headers.get("host")
  } catch {
    return false
  }
}
