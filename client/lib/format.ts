import { format, formatDistanceToNow } from "date-fns"

// Defaults from server/app/core/config.py. The server is the authority and
// enforces them; these only drive client-side hints and early validation.
const MB = 1024 * 1024

/** Size limits are configured in megabytes; everything downstream uses bytes. */
function envMegabytes(value: string | undefined, fallbackMb: number): number {
  const mb = Number(value)
  return (Number.isFinite(mb) && mb > 0 ? mb : fallbackMb) * MB
}

export const LIMITS = {
  uploadBytes: envMegabytes(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB, 25),
  submissionQuota: Number(process.env.NEXT_PUBLIC_USER_SUBMISSION_QUOTA ?? 5),
  storageQuotaBytes: envMegabytes(process.env.NEXT_PUBLIC_USER_STORAGE_QUOTA_MB, 200),
  errorMessageChars: Number(process.env.NEXT_PUBLIC_MAX_ERROR_MESSAGE_CHARS ?? 8000),
  passwordMin: 10,
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B"
  const units = ["B", "KB", "MB", "GB"]
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** i
  return `${value >= 10 || i === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[i]}`
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return formatDistanceToNow(d, { addSuffix: true })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "—"
  return format(d, "MMM d, yyyy 'at' h:mm a")
}

export function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase())
      .join("") || "?"
  )
}
