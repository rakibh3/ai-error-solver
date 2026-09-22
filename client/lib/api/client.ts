// Browser-side HTTP client. Every request goes to the same-origin BFF proxy
// (app/api/backend/[...path]/route.ts), which attaches the bearer token from
// the httpOnly session cookie. The token never reaches client JavaScript.

export const BACKEND_PREFIX = "/api/backend"
export const SESSION_EXPIRED_EVENT = "session-expired"

export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

type ValidationItem = { loc?: (string | number)[]; msg?: string }

/**
 * Normalise the server's three error shapes into one ApiError:
 *  - `{ detail: "..." }`                    HTTPException
 *  - `{ detail: [{ loc, msg }, ...] }`       422 validation
 *  - `{ error: "Rate limit exceeded: ..." }` 429 from slowapi
 */
export function toApiError(status: number, body: unknown): ApiError {
  const data = (body ?? {}) as { detail?: unknown; error?: unknown; message?: unknown }

  if (Array.isArray(data.detail)) {
    const fieldErrors: Record<string, string> = {}
    const messages: string[] = []
    for (const item of data.detail as ValidationItem[]) {
      const msg = (item.msg ?? "Invalid value").replace(/^Value error, /, "")
      const field = item.loc?.filter((p) => p !== "body").join(".")
      if (field && !fieldErrors[field]) fieldErrors[field] = msg
      messages.push(field ? `${field}: ${msg}` : msg)
    }
    return new ApiError(status, messages[0] ?? "Validation failed", fieldErrors)
  }

  if (typeof data.detail === "string") return new ApiError(status, data.detail)
  if (typeof data.error === "string") {
    return new ApiError(status, status === 429 ? `Too many requests. ${data.error}.` : data.error)
  }
  if (typeof data.message === "string") return new ApiError(status, data.message)

  return new ApiError(status, defaultMessage(status))
}

function defaultMessage(status: number): string {
  if (status === 0) return "Could not reach the server. Check your connection."
  if (status === 401) return "Your session has expired. Please sign in again."
  if (status === 403) return "You do not have permission to do that."
  if (status === 404) return "Not found."
  if (status === 429) return "Too many requests. Please wait and try again."
  if (status >= 500) return "The server ran into a problem. Please try again."
  return `Request failed (${status}).`
}

function notifySessionExpired(status: number, path: string) {
  // Login itself returns 401 for bad credentials; that is not an expiry.
  if (status === 401 && typeof window !== "undefined" && !path.includes("/auth/login")) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  }
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return { detail: text }
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"
  json?: unknown
  body?: BodyInit
  query?: Record<string, string | number | undefined | null>
  signal?: AbortSignal
}

export function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v))
  }
  const suffix = qs.toString()
  return `${BACKEND_PREFIX}${path}${suffix ? `?${suffix}` : ""}`
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" }
  let body = opts.body
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json"
    body = JSON.stringify(opts.json)
  }

  let res: Response
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers,
      body,
      signal: opts.signal,
      cache: "no-store",
      credentials: "same-origin",
    })
  } catch (err) {
    if ((err as Error)?.name === "AbortError") throw err
    throw new ApiError(0, defaultMessage(0))
  }

  const data = await parseBody(res)
  if (!res.ok) {
    notifySessionExpired(res.status, path)
    throw toApiError(res.status, data)
  }
  return data as T
}

/**
 * Multipart POST via XHR, because fetch() still cannot report upload progress.
 */
export function uploadWithProgress<T>(
  path: string,
  form: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", buildUrl(path), true)
    xhr.setRequestHeader("Accept", "application/json")

    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable && onProgress) onProgress((evt.loaded / evt.total) * 100)
    }
    xhr.onload = () => {
      let data: unknown = null
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        data = { detail: xhr.responseText }
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T)
      } else {
        notifySessionExpired(xhr.status, path)
        reject(toApiError(xhr.status, data))
      }
    }
    xhr.onerror = () => reject(new ApiError(0, defaultMessage(0)))
    xhr.send(form)
  })
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return "Something went wrong."
}
