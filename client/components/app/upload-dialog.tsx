"use client"

import * as React from "react"
import { AlertCircle, Files, FolderOpen, Loader2, UploadCloud } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { errorMessage } from "@/lib/api/client"
import { createSubmission } from "@/lib/api/endpoints"
import type { Submission } from "@/lib/api/types"
import { LIMITS, formatBytes } from "@/lib/format"
import { cn } from "@/lib/utils"

// Mirrors PRUNE_DIRS / PRUNE_FILES in server/app/utils/archive.py. The server
// strips these anyway; skipping them here keeps the upload small.
const IGNORED_DIRS = new Set([
  "node_modules", "dist", "build", "out", ".next", ".nuxt", "venv", ".venv",
  "__pycache__", ".pytest_cache", ".git", ".vercel", ".netlify", "coverage",
  ".idea", ".vscode", ".cache",
])
const IGNORED_FILES = new Set([
  "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
  "Pipfile.lock", "poetry.lock", ".DS_Store", "Thumbs.db",
])
// Server-side archive limits (MAX_ARCHIVE_MEMBERS, MAX_MEMBER_BYTES, MAX_EXTRACTED_BYTES).
const MAX_FILES = 2000
const MAX_FILE_BYTES = 10 * 1024 * 1024
const MAX_EXTRACTED_BYTES = 50 * 1024 * 1024

type Mode = "folder" | "files"
type Phase = "idle" | "zipping" | "uploading"

/** Loose files to be zipped on the device: a whole folder, or hand-picked files. */
interface FolderSelection {
  kind: "folder"
  source: "folder" | "files"
  rootName: string
  files: { path: string; file: File }[]
  skipped: number
  totalBytes: number
}
interface ZipSelection {
  kind: "zip"
  file: File
}
type Selection = FolderSelection | ZipSelection

function isIgnored(relPath: string): boolean {
  const parts = relPath.split("/")
  const name = parts[parts.length - 1]
  return IGNORED_FILES.has(name) || parts.slice(0, -1).some((p) => IGNORED_DIRS.has(p))
}

function readFolder(list: FileList): FolderSelection {
  const files: FolderSelection["files"] = []
  let skipped = 0
  let totalBytes = 0
  let rootName = ""
  for (const file of Array.from(list)) {
    const full = file.webkitRelativePath || file.name
    const parts = full.split("/").filter(Boolean)
    if (!rootName && parts.length > 1) rootName = parts[0]
    const rel = parts.length > 1 ? parts.slice(1).join("/") : parts.join("/")
    if (!rel || isIgnored(rel)) {
      skipped++
      continue
    }
    files.push({ path: rel, file })
    totalBytes += file.size
  }
  return { kind: "folder", source: "folder", rootName: rootName || "project", files, skipped, totalBytes }
}

/**
 * Hand-picked files. A single .zip is uploaded as-is; anything else is zipped
 * on the device with every file at the archive root.
 */
function readFiles(list: FileList): Selection {
  const picked = Array.from(list)
  if (picked.length === 1 && /\.zip$/i.test(picked[0].name)) {
    return { kind: "zip", file: picked[0] }
  }

  const files: FolderSelection["files"] = []
  const used = new Set<string>()
  let skipped = 0
  let totalBytes = 0
  for (const file of picked) {
    if (isIgnored(file.name)) {
      skipped++
      continue
    }
    // Same-named files from different folders would overwrite each other in
    // the zip; keep both as "name (2).ext".
    let path = file.name
    for (let n = 2; used.has(path); n++) {
      const dot = file.name.lastIndexOf(".")
      path = dot > 0 ? `${file.name.slice(0, dot)} (${n})${file.name.slice(dot)}` : `${file.name} (${n})`
    }
    used.add(path)
    files.push({ path, file })
    totalBytes += file.size
  }

  const rootName =
    files.length === 1 ? files[0].path.replace(/\.[^.]+$/, "") || "file" : "files"
  return { kind: "folder", source: "files", rootName, files, skipped, totalBytes }
}

function validate(sel: Selection): string | null {
  if (sel.kind === "zip") {
    if (!/\.zip$/i.test(sel.file.name)) return "Please choose a .zip file."
    if (sel.file.size > LIMITS.uploadBytes) {
      return `This archive is ${formatBytes(sel.file.size)}. The upload limit is ${formatBytes(LIMITS.uploadBytes)}.`
    }
    return null
  }
  const what = sel.source === "folder" ? "This folder has" : "You selected"
  if (sel.files.length === 0) {
    return sel.source === "folder"
      ? "No source files found in that folder after skipping build artefacts."
      : "Only lockfiles or system files were selected. Choose your source files."
  }
  if (sel.files.length > MAX_FILES) {
    return `${what} ${sel.files.length.toLocaleString()} files. The limit is ${MAX_FILES.toLocaleString()}.`
  }
  const big = sel.files.find((f) => f.file.size > MAX_FILE_BYTES)
  if (big) return `${big.path} is ${formatBytes(big.file.size)}. Individual files must be under ${formatBytes(MAX_FILE_BYTES)}.`
  if (sel.totalBytes > MAX_EXTRACTED_BYTES) {
    return `Source files total ${formatBytes(sel.totalBytes)}. The limit is ${formatBytes(MAX_EXTRACTED_BYTES)}.`
  }
  return null
}

export function UploadDialog(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onUploaded: (submission: Submission) => void
}) {
  const folderInput = React.useRef<HTMLInputElement>(null)
  const filesInput = React.useRef<HTMLInputElement>(null)
  const [mode, setMode] = React.useState<Mode>("folder")
  const [selection, setSelection] = React.useState<Selection | null>(null)
  const [displayName, setDisplayName] = React.useState("")
  const [phase, setPhase] = React.useState<Phase>("idle")
  const [progress, setProgress] = React.useState(0)
  const [error, setError] = React.useState<string | null>(null)

  const busy = phase !== "idle"
  const validationError = selection ? validate(selection) : null

  // `webkitdirectory` is what turns a file input into a folder picker, and
  // React has no typed prop for it. Set it from a callback ref: the dialog
  // content mounts through a portal a render *after* `open` flips, so an
  // effect keyed on `open` ran while the ref was still null and the attribute
  // was never applied -- the "Folder" tab silently picked files instead.
  const setFolderInput = React.useCallback((el: HTMLInputElement | null) => {
    folderInput.current = el
    if (el) {
      el.setAttribute("webkitdirectory", "")
      el.setAttribute("directory", "")
    }
  }, [])

  function reset() {
    setSelection(null)
    setDisplayName("")
    setPhase("idle")
    setProgress(0)
    setError(null)
  }

  function handleOpenChange(open: boolean) {
    if (busy) return // don't abandon an upload mid-flight
    if (!open) reset()
    props.onOpenChange(open)
  }

  function onFolderPicked(list: FileList | null) {
    if (!list?.length) return
    const sel = readFolder(list)
    setSelection(sel)
    setError(null)
    if (!displayName) setDisplayName(sel.rootName)
  }

  function onFilesPicked(list: FileList | null) {
    if (!list?.length) return
    const sel = readFiles(list)
    setSelection(sel)
    setError(null)
    if (!displayName) {
      setDisplayName(sel.kind === "zip" ? sel.file.name.replace(/\.zip$/i, "") : sel.rootName)
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!selection || validationError || !displayName.trim()) return
    setError(null)

    try {
      let blob: Blob
      let fileName: string
      if (selection.kind === "folder") {
        setPhase("zipping")
        setProgress(0)
        const { default: JSZip } = await import("jszip")
        const zip = new JSZip()
        for (const { path, file } of selection.files) zip.file(path, file)
        blob = await zip.generateAsync(
          { type: "blob", compression: "DEFLATE", compressionOptions: { level: 6 } },
          (meta) => setProgress(Math.round(meta.percent)),
        )
        fileName = `${selection.rootName}.zip`
        if (blob.size > LIMITS.uploadBytes) {
          throw new Error(
            `The compressed project is ${formatBytes(blob.size)}. The upload limit is ${formatBytes(LIMITS.uploadBytes)}.`,
          )
        }
      } else {
        blob = selection.file
        fileName = selection.file.name
      }

      setPhase("uploading")
      setProgress(0)
      const submission = await createSubmission(displayName.trim(), blob, fileName, (pct) =>
        setProgress(Math.round(pct)),
      )
      reset()
      props.onUploaded(submission)
    } catch (err) {
      setError(errorMessage(err))
      setPhase("idle")
      setProgress(0)
    }
  }

  return (
    <Dialog open={props.open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={onSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>Upload a project</DialogTitle>
            <DialogDescription>
              Pick your whole project folder, or choose individual files — even just one — or a .zip
              you already have. Build folders like node_modules, .venv and .git are skipped
              automatically.
            </DialogDescription>
          </DialogHeader>

          <Tabs
            value={mode}
            onValueChange={(v) => {
              setMode(v as Mode)
              setSelection(null)
              setError(null)
            }}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="folder" disabled={busy}>
                <FolderOpen />
                Folder
              </TabsTrigger>
              <TabsTrigger value="files" disabled={busy}>
                <Files />
                Files or .zip
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <input
            ref={setFolderInput}
            type="file"
            multiple
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(e) => {
              onFolderPicked(e.currentTarget.files)
              e.currentTarget.value = ""
            }}
          />
          {/* No `accept`: any source file (or one .zip) can be picked, singly or several at once. */}
          <input
            ref={filesInput}
            type="file"
            multiple
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(e) => {
              onFilesPicked(e.currentTarget.files)
              e.currentTarget.value = ""
            }}
          />

          <button
            type="button"
            disabled={busy}
            onClick={() => (mode === "folder" ? folderInput : filesInput).current?.click()}
            className={cn(
              "flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
              "hover:border-emerald-400 hover:bg-emerald-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:hover:bg-emerald-950/30",
              selection && !validationError && "border-emerald-500/50 bg-emerald-50/40 dark:bg-emerald-950/20",
              validationError && "border-destructive/50",
            )}
          >
            <UploadCloud className="size-8 text-emerald-400" />
            {selection ? <SelectionSummary selection={selection} /> : (
              <>
                <span className="text-sm font-medium">
                  {mode === "folder"
                    ? "Choose a project folder"
                    : "Choose one or more files, or a .zip"}
                </span>
                <span className="text-xs text-muted-foreground">
                  Up to {formatBytes(LIMITS.uploadBytes)} compressed · {MAX_FILES.toLocaleString()} files
                </span>
              </>
            )}
          </button>

          <div className="space-y-2">
            <Label htmlFor="display-name">Name</Label>
            <Input
              id="display-name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Routing assignment"
              maxLength={255}
              disabled={busy}
              required
            />
            <p className="text-xs text-muted-foreground">A label to help you recognise this upload later.</p>
          </div>

          {busy && (
            <div className="space-y-2" aria-live="polite">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{phase === "zipping" ? "Compressing on your device…" : "Uploading…"}</span>
                <span className="tabular-nums">{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
          )}

          {(validationError || error) && (
            <Alert variant="destructive" role="alert">
              <AlertCircle className="size-4" />
              <AlertDescription>{validationError ?? error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={busy}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={busy || !selection || Boolean(validationError) || !displayName.trim()}
            >
              {busy ? <Loader2 className="animate-spin" /> : <UploadCloud />}
              {phase === "zipping" ? "Compressing…" : phase === "uploading" ? "Uploading…" : "Upload"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function SelectionSummary({ selection }: { selection: Selection }) {
  if (selection.kind === "zip") {
    return (
      <>
        <span className="max-w-full truncate text-sm font-medium">{selection.file.name}</span>
        <span className="text-xs text-muted-foreground">{formatBytes(selection.file.size)} · click to change</span>
      </>
    )
  }
  const count = selection.files.length
  const title =
    selection.source === "folder"
      ? `${selection.rootName}/`
      : count === 1
        ? selection.files[0].path
        : `${count.toLocaleString()} files selected`
  return (
    <>
      <span className="max-w-full truncate text-sm font-medium">{title}</span>
      <span className="text-xs text-muted-foreground">
        {count.toLocaleString()} {count === 1 ? "file" : "files"} · {formatBytes(selection.totalBytes)}
        {selection.skipped > 0 && ` · ${selection.skipped.toLocaleString()} skipped`} · click to change
      </span>
    </>
  )
}
