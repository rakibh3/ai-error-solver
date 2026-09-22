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
 * The browser's IP, forwarded to the API as X-Forwarded-For so its per-IP rate
 * limits see real clients instead of this server's address.
 *
 * Next.js sets X-Forwarded-For to the socket address only when the header is
 * absent, so a client can supply its own. TRUSTED_PROXY_HOPS is the number of
 * reverse proxies in front of Next.js that append to the header: the client is
 * the entry that many places from the right. With 0 (no proxy) the rightmost
 * entry is used, which a client talking to Next.js directly can spoof -- the
 * API's per-account login limit still applies in that case.
 */
export function clientIp(request: Request): string | null {
  const entries = (request.headers.get("x-forwarded-for") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
  if (entries.length === 0) return null
  const hops = Math.max(1, Number.parseInt(process.env.TRUSTED_PROXY_HOPS ?? "0", 10) || 0)
  return entries[Math.max(0, entries.length - hops)] ?? null
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
