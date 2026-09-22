// One function per server endpoint. Paths are the server's own paths; the BFF
// proxy forwards them verbatim. Login and logout are the exception: they go to
// the Next.js auth routes, which own the httpOnly session cookie.

import { ApiError, request, toApiError, uploadWithProgress } from "./client"
import type {
  AdminProject,
  Analysis,
  AnalyzePayload,
  CatalogBranch,
  CatalogProject,
  CollectionsHealth,
  DeleteResponse,
  IngestAccepted,
  LoginPayload,
  ReindexAccepted,
  RegisterPayload,
  RootStatus,
  Submission,
  User,
  UserRole,
} from "./types"

const V1 = "/api/v1"

// --- Root -------------------------------------------------------------------

/** GET / — liveness check. */
export const getServerStatus = () => request<RootStatus>("")

// --- Authentication ---------------------------------------------------------

/** POST /api/v1/auth/register */
export const register = (payload: RegisterPayload) =>
  request<User>(`${V1}/auth/register`, { method: "POST", json: payload })

/** POST /api/v1/auth/login — via the Next.js route that stores the token in a cookie. */
export async function login(payload: LoginPayload): Promise<User> {
  let res: Response
  try {
    res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    })
  } catch {
    throw new ApiError(0, "Could not reach the server. Check your connection.")
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) throw toApiError(res.status, data)
  return (data as { user: User }).user
}

/** Clears the session cookie. The server has no logout endpoint; JWTs expire on their own. */
export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" }).catch(() => {})
}

/** GET /api/v1/auth/me */
export const getMe = () => request<User>(`${V1}/auth/me`)

// --- Catalog ----------------------------------------------------------------

/** GET /api/v1/catalog/projects */
export const listCatalogProjects = () => request<CatalogProject[]>(`${V1}/catalog/projects`)

/** GET /api/v1/catalog/projects/{project_id}/branches */
export const listCatalogBranches = (projectId: string) =>
  request<CatalogBranch[]>(`${V1}/catalog/projects/${encodeURIComponent(projectId)}/branches`)

// --- Submissions ------------------------------------------------------------

/** POST /api/v1/submissions (multipart: display_name + file) */
export function createSubmission(
  displayName: string,
  file: Blob,
  fileName: string,
  onProgress?: (percent: number) => void,
) {
  const form = new FormData()
  form.append("display_name", displayName)
  form.append("file", file, fileName)
  return uploadWithProgress<Submission>(`${V1}/submissions`, form, onProgress)
}

/** GET /api/v1/submissions */
export const listSubmissions = () => request<Submission[]>(`${V1}/submissions`)

/** GET /api/v1/submissions/{submission_id} */
export const getSubmission = (id: string) =>
  request<Submission>(`${V1}/submissions/${encodeURIComponent(id)}`)

/** DELETE /api/v1/submissions/{submission_id} */
export const deleteSubmission = (id: string) =>
  request<DeleteResponse>(`${V1}/submissions/${encodeURIComponent(id)}`, { method: "DELETE" })

/** POST /api/v1/submissions/{submission_id}/analyze */
export const analyzeSubmission = (id: string, payload: AnalyzePayload) =>
  request<Analysis>(`${V1}/submissions/${encodeURIComponent(id)}/analyze`, {
    method: "POST",
    json: payload,
  })

/** GET /api/v1/submissions/{submission_id}/analyses */
export const listAnalyses = (id: string) =>
  request<Analysis[]>(`${V1}/submissions/${encodeURIComponent(id)}/analyses`)

// --- Admin ------------------------------------------------------------------

/** POST /api/v1/admin/reference-projects */
export const ingestReferenceProject = (repoUrl: string) =>
  request<IngestAccepted>(`${V1}/admin/reference-projects`, {
    method: "POST",
    json: { repo_url: repoUrl },
  })

/** GET /api/v1/admin/reference-projects */
export const listReferenceProjects = () =>
  request<AdminProject[]>(`${V1}/admin/reference-projects`)

/** GET /api/v1/admin/reference-projects/health */
export const getCollectionsHealth = () =>
  request<CollectionsHealth>(`${V1}/admin/reference-projects/health`)

/** POST /api/v1/admin/reference-projects/{project_id}/reindex[?branch=] */
export const reindexReferenceProject = (projectId: string, branch?: string) =>
  request<ReindexAccepted>(
    `${V1}/admin/reference-projects/${encodeURIComponent(projectId)}/reindex`,
    { method: "POST", query: { branch } },
  )

/** DELETE /api/v1/admin/reference-projects/{project_id} */
export const deleteReferenceProject = (projectId: string) =>
  request<DeleteResponse>(`${V1}/admin/reference-projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
  })

/** GET /api/v1/admin/users?limit=&offset= */
export const listUsers = (limit = 50, offset = 0) =>
  request<User[]>(`${V1}/admin/users`, { query: { limit, offset } })

/** PATCH /api/v1/admin/users/{user_id}/role */
export const updateUserRole = (userId: number, role: UserRole) =>
  request<User>(`${V1}/admin/users/${userId}/role`, { method: "PATCH", json: { role } })

// --- SWR keys ---------------------------------------------------------------

export const keys = {
  me: "me",
  serverStatus: "server-status",
  catalogProjects: "catalog-projects",
  catalogBranches: (projectId: string) => ["catalog-branches", projectId] as const,
  submissions: "submissions",
  submission: (id: string) => ["submission", id] as const,
  analyses: (id: string) => ["analyses", id] as const,
  referenceProjects: "admin-reference-projects",
  health: "admin-health",
  users: (limit: number, offset: number) => ["admin-users", limit, offset] as const,
}
