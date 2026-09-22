// Mirrors the Pydantic schemas in server/app/schemas. Keep in sync with
// GET /api/v1/openapi.json when the server contract changes.

export type UserRole = "ADMIN" | "USER"

export interface User {
  id: number
  fullname: string
  email: string
  role: UserRole
  is_active: boolean
}

export interface RegisterPayload {
  fullname: string
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

// --- Catalog ---------------------------------------------------------------

export interface CatalogProject {
  id: string
  name: string
  ready_branch_count: number
}

export interface CatalogBranch {
  id: string
  branch_name: string
  indexed_at: string | null
}

// --- Submissions & analyses -----------------------------------------------

export interface Submission {
  id: string
  owner_id: number
  display_name: string
  file_count: number
  total_bytes: number
  created_at: string
}

export interface AnalyzePayload {
  branch_id: string
  error_message: string
}

export interface CodeChange {
  old_code: string
  new_code: string
}

export interface FixInstruction {
  file: string
  line: number | null
  change: CodeChange
}

export interface AnalysisResult {
  error_explanation: string
  fix_instructions: FixInstruction
}

export type AnalysisStatus = "success" | "failed"

export interface Analysis {
  id: string
  submission_id: string
  branch_id: string | null
  error_message: string
  status: AnalysisStatus
  result: AnalysisResult | null
  failure_reason: string | null
  model: string
  created_at: string
}

export interface DeleteResponse {
  status: string
  message: string
}

// --- Admin -----------------------------------------------------------------

export type BranchStatus = "pending" | "indexing" | "ready" | "failed"

export interface AdminBranch {
  id: string
  branch_name: string
  collection_name: string
  status: BranchStatus
  error: string | null
  files_indexed: number | null
  chunks_indexed: number | null
  indexed_at: string | null
}

export interface AdminProject {
  id: string
  name: string
  repo_url: string
  created_by: number | null
  created_at: string
  branches: AdminBranch[]
}

export interface IngestAccepted {
  status: string
  project_id: string
  name: string
  branches: string[]
  message: string
}

export interface ReindexAccepted {
  status: string
  message: string
}

export interface MissingCollection {
  branch_id: string
  branch_name: string
  collection_name: string
}

// `status: "error"` (Qdrant unreachable) comes back as a 200 with only `message`.
export interface CollectionsHealth {
  status: "success" | "error"
  message?: string
  total_branches?: number
  ready_branches?: number
  missing_collections?: MissingCollection[]
  orphaned_collections?: string[]
}

export interface RootStatus {
  message: string
}
