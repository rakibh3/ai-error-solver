"use client"

import * as React from "react"
import useSWR from "swr"
import { toast } from "sonner"
import {
  CheckCircle2,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  ExternalLink,
  FolderGit2,
  XCircle,
  GitBranch,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCw,
  RotateCw,
  Trash2,
} from "lucide-react"
import {
  BranchStatusBadge,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  PageHeader,
} from "@/components/app/common"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { ApiError, errorMessage } from "@/lib/api/client"
import {
  deleteReferenceProject,
  ingestReferenceProject,
  keys,
  listReferenceProjects,
  reindexReferenceProject,
} from "@/lib/api/endpoints"
import type { AdminBranch, AdminProject } from "@/lib/api/types"
import { formatDateTime, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

const POLL_MS = 3000
// Background work may not have flipped a branch to `pending` by the time the
// 202 returns, so keep polling briefly after any ingest/re-index request.
const GRACE_MS = 15000

function isBusy(b: AdminBranch) {
  return b.status === "pending" || b.status === "indexing"
}

/** Projects start expanded only when something is in progress or failed. */
function needsAttention(p: AdminProject) {
  return p.branches.some((b) => isBusy(b) || b.status === "failed")
}

export default function ReferencesPage() {
  const [pollUntil, setPollUntil] = React.useState(0)
  // Stable reference: SWR re-arms its poll timer whenever this function changes.
  const refreshInterval = React.useCallback(
    (data: AdminProject[] | undefined) =>
      data?.some((p) => p.branches.some(isBusy)) || Date.now() < pollUntil ? POLL_MS : 0,
    [pollUntil],
  )
  const projects = useSWR(keys.referenceProjects, listReferenceProjects, { refreshInterval })
  const [toDelete, setToDelete] = React.useState<AdminProject | null>(null)
  // Explicit open/closed choices per project; unset ones follow needsAttention().
  const [expanded, setExpanded] = React.useState<Record<string, boolean>>({})
  const setAllExpanded = (list: AdminProject[], open: boolean) =>
    setExpanded(Object.fromEntries(list.map((p) => [p.id, open])))

  const kickPolling = React.useCallback(() => {
    setPollUntil(Date.now() + GRACE_MS)
    void projects.mutate()
  }, [projects])

  async function reindex(project: AdminProject, branch?: string) {
    try {
      const res = await reindexReferenceProject(project.id, branch)
      toast.success("Re-index queued", { description: res.message })
      kickPolling()
    } catch (err) {
      toast.error("Could not start re-indexing", { description: errorMessage(err) })
    }
  }

  const totals = React.useMemo(() => {
    const all = projects.data?.flatMap((p) => p.branches) ?? []
    return {
      ready: all.filter((b) => b.status === "ready").length,
      busy: all.filter(isBusy).length,
      failed: all.filter((b) => b.status === "failed").length,
    }
  }, [projects.data])

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reference projects"
        description="Repositories users compare their code against. Every branch is indexed separately and only appears to users once it is ready."
        actions={
          <Button variant="outline" onClick={() => projects.mutate()} disabled={projects.isValidating}>
            <RefreshCw className={projects.isValidating ? "animate-spin" : undefined} />
            Refresh
          </Button>
        }
      />

      <IngestCard onQueued={kickPolling} />

      {projects.data && projects.data.length > 0 && (
        <div className="flex flex-wrap gap-2 text-sm" aria-live="polite">
          <Badge variant="outline" className="border-emerald-200 text-emerald-800">{totals.ready} ready</Badge>
          {totals.busy > 0 && (
            <Badge variant="outline" className="gap-1 border-amber-200 text-amber-800">
              <Loader2 className="size-3 animate-spin" />
              {totals.busy} in progress · auto-refreshing
            </Badge>
          )}
          {totals.failed > 0 && (
            <Badge variant="outline" className="border-red-200 text-red-700">{totals.failed} failed</Badge>
          )}
        </div>
      )}

      {projects.error ? (
        <ErrorState error={projects.error} onRetry={() => projects.mutate()} />
      ) : projects.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      ) : !projects.data?.length ? (
        <EmptyState
          icon={<FolderGit2 className="size-6" />}
          title="No reference projects yet"
          description="Add a repository above. Its branches will be cloned and indexed in the background."
        />
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm text-muted-foreground">
              {projects.data.length} {projects.data.length === 1 ? "project" : "projects"}
            </p>
            <div className="flex items-center gap-1">
              <Button size="sm" variant="ghost" onClick={() => setAllExpanded(projects.data!, true)}>
                <ChevronsUpDown />
                Expand all
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setAllExpanded(projects.data!, false)}>
                <ChevronsDownUp />
                Collapse all
              </Button>
            </div>
          </div>
          {projects.data.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              open={expanded[p.id] ?? needsAttention(p)}
              onOpenChange={(open) => setExpanded((prev) => ({ ...prev, [p.id]: open }))}
              onReindexAll={() => reindex(p)}
              onReindexBranch={(b) => reindex(p, b)}
              onDelete={() => setToDelete(p)}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={Boolean(toDelete)}
        onOpenChange={(o) => !o && setToDelete(null)}
        title={`Delete “${toDelete?.name}”?`}
        description={
          <>
            <p>
              This removes every branch, its vector collections, and the cloned files. Users will no longer be
              able to compare against it.
            </p>
            <p>Past analyses are kept, but will show the reference as deleted.</p>
            <p className="font-medium text-foreground">This cannot be undone.</p>
          </>
        }
        confirmLabel="Delete reference"
        destructive
        onConfirm={async () => {
          if (!toDelete) return
          try {
            const res = await deleteReferenceProject(toDelete.id)
            toast.success("Reference deleted", { description: res.message })
            await projects.mutate((list) => list?.filter((p) => p.id !== toDelete.id), { revalidate: true })
          } catch (err) {
            toast.error("Could not delete reference", { description: errorMessage(err) })
            throw err
          }
        }}
      />
    </div>
  )
}

function IngestCard({ onQueued }: { onQueued: () => void }) {
  const [url, setUrl] = React.useState("")
  const [pending, setPending] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPending(true)
    setError(null)
    try {
      const res = await ingestReferenceProject(url.trim())
      toast.success(`Added “${res.name}”`, {
        description: `${res.message}: ${res.branches.join(", ")}`,
      })
      setUrl("")
      onQueued()
    } catch (err) {
      setError(
        err instanceof ApiError && err.fieldErrors.repo_url
          ? `Enter a valid HTTPS URL (${err.fieldErrors.repo_url}).`
          : errorMessage(err),
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Plus className="size-4 text-emerald-600" />
          Add a reference repository
        </CardTitle>
        <CardDescription>
          Paste an HTTPS clone URL. The project is named after the last part of the URL, which must be unique.
          Enumerating branches takes a few seconds; indexing continues in the background.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="flex-1 space-y-2">
            <Label htmlFor="repo-url" className="sr-only">
              Repository URL
            </Label>
            <Input
              id="repo-url"
              type="url"
              inputMode="url"
              placeholder="https://github.com/acme/fastapi-course.git"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                setError(null)
              }}
              aria-invalid={Boolean(error)}
              disabled={pending}
              required
            />
            {error && (
              <p className="text-xs font-medium text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>
          <Button type="submit" disabled={pending || !url.trim()} className="bg-emerald-600 hover:bg-emerald-700">
            {pending ? <Loader2 className="animate-spin" /> : <Plus />}
            {pending ? "Reading repository…" : "Add repository"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

function ProjectCard(props: {
  project: AdminProject
  open: boolean
  onOpenChange: (open: boolean) => void
  onReindexAll: () => void
  onReindexBranch: (branch: string) => void
  onDelete: () => void
}) {
  const p = props.project
  const branches = [...p.branches].sort((a, b) => a.branch_name.localeCompare(b.branch_name))
  const busy = branches.some(isBusy)
  const counts = {
    ready: branches.filter((b) => b.status === "ready").length,
    busy: branches.filter(isBusy).length,
    failed: branches.filter((b) => b.status === "failed").length,
  }
  const contentId = `project-${p.id}-branches`

  return (
    <Collapsible open={props.open} onOpenChange={props.onOpenChange} asChild>
      <Card className="gap-0 overflow-hidden py-0">
        <div
          className={cn(
            "flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between",
            props.open && "border-b",
          )}
        >
          <div className="min-w-0 space-y-1">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                aria-controls={contentId}
                className="group -m-1 flex max-w-full items-center gap-2 rounded-md p-1 text-left hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
              >
                <ChevronRight
                  aria-hidden="true"
                  className="size-4 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-90"
                />
                <FolderGit2 className="size-4 shrink-0 text-emerald-600" />
                <h2 className="truncate font-semibold">{p.name}</h2>
                <span className="sr-only">{props.open ? "Collapse branches" : "Expand branches"}</span>
              </button>
            </CollapsibleTrigger>
            <div className="flex flex-wrap items-center gap-1.5 pl-7" aria-label="Branch status summary">
              <Badge variant="secondary">
                {branches.length} {branches.length === 1 ? "branch" : "branches"}
              </Badge>
              {counts.ready > 0 && (
                <Badge variant="outline" className="gap-1 border-emerald-200 text-emerald-800 dark:border-emerald-900 dark:text-emerald-300">
                  <CheckCircle2 className="size-3" />
                  {counts.ready} ready
                </Badge>
              )}
              {counts.busy > 0 && (
                <Badge variant="outline" className="gap-1 border-amber-200 text-amber-800 dark:border-amber-900 dark:text-amber-300">
                  <Loader2 className="size-3 animate-spin" />
                  {counts.busy} indexing
                </Badge>
              )}
              {counts.failed > 0 && (
                <Badge variant="outline" className="gap-1 border-red-200 text-red-700 dark:border-red-900 dark:text-red-300">
                  <XCircle className="size-3" />
                  {counts.failed} failed
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pl-7 text-xs text-muted-foreground">
              <a
                href={p.repo_url}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex max-w-full items-center gap-1 truncate hover:text-foreground hover:underline"
              >
                {p.repo_url}
                <ExternalLink className="size-3 shrink-0" />
              </a>
              <span title={formatDateTime(p.created_at)}>Added {timeAgo(p.created_at)}</span>
              {p.created_by != null && <span>by admin #{p.created_by}</span>}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button size="sm" variant="outline" onClick={props.onReindexAll} disabled={busy}>
              <RotateCw />
              Re-index all
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="icon" variant="ghost" aria-label={`More actions for ${p.name}`}>
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <a href={p.repo_url} target="_blank" rel="noreferrer noopener">
                    <ExternalLink />
                    Open repository
                  </a>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onSelect={props.onDelete}>
                  <Trash2 />
                  Delete reference
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <CollapsibleContent id={contentId}>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="pl-4">Branch</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Files</TableHead>
                <TableHead className="hidden text-right sm:table-cell">Chunks</TableHead>
                <TableHead className="hidden md:table-cell">Indexed</TableHead>
                <TableHead className="w-12 pr-4">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {branches.map((b) => (
                <TableRow key={b.id} className="align-top">
                  <TableCell className="max-w-[18rem] pl-4">
                    <div className="flex items-center gap-2">
                      <GitBranch className="size-3.5 shrink-0 text-muted-foreground" />
                      <span className="truncate font-mono text-xs">{b.branch_name}</span>
                    </div>
                    {b.status === "failed" && b.error && (
                      <p className="mt-1.5 whitespace-normal break-words text-xs text-destructive">{b.error}</p>
                    )}
                    <p className="mt-1 hidden truncate font-mono text-[10px] text-muted-foreground lg:block" title={b.collection_name}>
                      {b.collection_name}
                    </p>
                  </TableCell>
                  <TableCell>
                    <BranchStatusBadge status={b.status} />
                  </TableCell>
                  <TableCell className="hidden text-right tabular-nums sm:table-cell">
                    {b.files_indexed?.toLocaleString() ?? "—"}
                  </TableCell>
                  <TableCell className="hidden text-right tabular-nums sm:table-cell">
                    {b.chunks_indexed?.toLocaleString() ?? "—"}
                  </TableCell>
                  <TableCell className="hidden text-xs text-muted-foreground md:table-cell" title={formatDateTime(b.indexed_at)}>
                    {timeAgo(b.indexed_at)}
                  </TableCell>
                  <TableCell className="pr-4">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="size-8"
                          onClick={() => props.onReindexBranch(b.branch_name)}
                          disabled={isBusy(b)}
                          aria-label={`Re-index ${b.branch_name}`}
                        >
                          <RotateCw className="size-3.5" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>{b.status === "failed" ? "Retry indexing" : "Re-index this branch"}</TooltipContent>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}
