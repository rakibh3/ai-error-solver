"use client"

import * as React from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import useSWR from "swr"
import { toast } from "sonner"
import {
  ArrowLeft,
  FileQuestion,
  GitCompare,
  History,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
} from "lucide-react"
import { AnalysisMeta, AnalysisResultView } from "@/components/app/analysis-view"
import { ConfirmDialog, EmptyState, ErrorState } from "@/components/app/common"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { useSession } from "@/hooks/use-session"
import { ApiError, errorMessage } from "@/lib/api/client"
import {
  analyzeSubmission,
  deleteSubmission,
  getSubmission,
  keys,
  listAnalyses,
  listCatalogBranches,
  listCatalogProjects,
} from "@/lib/api/endpoints"
import type { Analysis, CatalogBranch, CatalogProject } from "@/lib/api/types"
import { LIMITS, formatBytes, formatDateTime, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

type BranchIndex = Map<string, { project: CatalogProject; branch: CatalogBranch }>

/** Resolve analysis.branch_id to a readable "project / branch" label. */
async function loadBranchIndex(): Promise<BranchIndex> {
  const projects = await listCatalogProjects()
  const index: BranchIndex = new Map()
  const lists = await Promise.all(projects.map((p) => listCatalogBranches(p.id).catch(() => [])))
  projects.forEach((project, i) => {
    for (const branch of lists[i]) index.set(branch.id, { project, branch })
  })
  return index
}

export default function SubmissionPage() {
  const { id } = useParams<{ id: string }>()
  // Remount per submission so local state (latest result, form) never leaks across ids.
  return <SubmissionView key={id} id={id} />
}

function SubmissionView({ id }: { id: string }) {
  const router = useRouter()
  const { user } = useSession()

  const submission = useSWR(keys.submission(id), () => getSubmission(id))
  const analyses = useSWR(submission.data ? keys.analyses(id) : null, () => listAnalyses(id))
  const branchIndex = useSWR("catalog-branch-index", loadBranchIndex, { revalidateOnFocus: false })

  const [latest, setLatest] = React.useState<Analysis | null>(null)
  const [prefill, setPrefill] = React.useState<{ branchId: string; projectId: string; error: string } | null>(null)
  const [deleteOpen, setDeleteOpen] = React.useState(false)
  const resultRef = React.useRef<HTMLDivElement>(null)
  const formRef = React.useRef<HTMLDivElement>(null)

  const branchLabel = React.useCallback(
    (branchId: string | null) => {
      if (!branchId) return "a deleted reference"
      const hit = branchIndex.data?.get(branchId)
      return hit ? `${hit.project.name} / ${hit.branch.branch_name}` : "an unavailable reference"
    },
    [branchIndex.data],
  )

  if (submission.error) {
    const notFound = submission.error instanceof ApiError && submission.error.status === 404
    return (
      <div className="space-y-6">
        <BackLink />
        {notFound ? (
          <EmptyState
            icon={<FileQuestion className="size-6" />}
            title="Submission not found"
            description="It may have been deleted, or it belongs to another account."
            action={
              <Button asChild variant="outline">
                <Link href="/dashboard">Back to submissions</Link>
              </Button>
            }
          />
        ) : (
          <ErrorState error={submission.error} onRetry={() => submission.mutate()} />
        )}
      </div>
    )
  }

  const s = submission.data

  return (
    <div className="space-y-6">
      <BackLink />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          {s ? (
            <>
              <h1 className="truncate text-2xl font-semibold tracking-tight">{s.display_name}</h1>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                <span>{s.file_count.toLocaleString()} files</span>
                <span>{formatBytes(s.total_bytes)}</span>
                <time dateTime={s.created_at} title={formatDateTime(s.created_at)}>
                  Uploaded {timeAgo(s.created_at)}
                </time>
                {user && s.owner_id !== user.id && <Badge variant="outline">User #{s.owner_id}</Badge>}
              </div>
            </>
          ) : (
            <>
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-48" />
            </>
          )}
        </div>
        <Button variant="outline" onClick={() => setDeleteOpen(true)} disabled={!s}>
          <Trash2 />
          Delete
        </Button>
      </div>

      <div ref={formRef} className="scroll-mt-20">
        <AnalyzeCard
          submissionId={id}
          disabled={!s}
          prefill={prefill}
          onResult={(analysis) => {
            setLatest(analysis)
            void analyses.mutate((list) => [analysis, ...(list ?? []).filter((a) => a.id !== analysis.id)], {
              revalidate: false,
            })
            requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }))
          }}
        />
      </div>

      {latest && (
        <div ref={resultRef} className="scroll-mt-20">
          <Card className={cn(latest.status === "success" && "border-emerald-300 dark:border-emerald-800")}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="size-4 text-emerald-400" />
                Latest result
              </CardTitle>
              <AnalysisMeta analysis={latest} branchLabel={branchLabel(latest.branch_id)} />
            </CardHeader>
            <CardContent>
              <AnalysisResultView analysis={latest} />
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <History className="size-4 text-muted-foreground" />
            Analysis history
            {analyses.data && (
              <Badge variant="secondary" className="tabular-nums">
                {analyses.data.length}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>Every comparison run against this submission, newest first — including failed attempts.</CardDescription>
        </CardHeader>
        <CardContent>
          {analyses.error ? (
            <ErrorState error={analyses.error} onRetry={() => analyses.mutate()} />
          ) : !analyses.data ? (
            <div className="space-y-2">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : analyses.data.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No analyses yet. Run your first comparison above.
            </p>
          ) : (
            <Accordion type="single" collapsible className="w-full">
              {analyses.data.map((a) => (
                <AccordionItem key={a.id} value={a.id}>
                  <AccordionTrigger className="hover:no-underline">
                    <div className="min-w-0 flex-1 space-y-1.5 text-left">
                      <p className="line-clamp-1 font-mono text-xs font-normal">{firstLine(a.error_message)}</p>
                      <AnalysisMeta analysis={a} branchLabel={branchLabel(a.branch_id)} />
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="space-y-1.5">
                      <div className="text-xs font-medium text-muted-foreground">Error you reported</div>
                      <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">{a.error_message}</pre>
                    </div>
                    <AnalysisResultView analysis={a} />
                    {a.branch_id && branchIndex.data?.has(a.branch_id) && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          const hit = branchIndex.data!.get(a.branch_id!)!
                          setPrefill({ projectId: hit.project.id, branchId: a.branch_id!, error: a.error_message })
                          formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
                        }}
                      >
                        <RotateCcw />
                        Run again
                      </Button>
                    )}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete this submission?"
        description={
          <>
            <p>
              “{s?.display_name}” will be permanently removed, along with its files and all{" "}
              {analyses.data?.length ?? 0} analyses.
            </p>
            <p className="font-medium text-foreground">This cannot be undone.</p>
          </>
        }
        confirmLabel="Delete submission"
        destructive
        onConfirm={async () => {
          try {
            await deleteSubmission(id)
            toast.success("Submission deleted")
            router.replace("/dashboard")
          } catch (err) {
            toast.error("Could not delete submission", { description: errorMessage(err) })
            throw err
          }
        }}
      />
    </div>
  )
}

function BackLink() {
  return (
    <Button asChild variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
      <Link href="/dashboard">
        <ArrowLeft />
        All submissions
      </Link>
    </Button>
  )
}

function firstLine(text: string): string {
  const lines = text.trim().split("\n").filter((l) => l.trim())
  // The last traceback line usually names the exception; prefer it.
  return lines[lines.length - 1] ?? text
}

function AnalyzeCard(props: {
  submissionId: string
  disabled: boolean
  prefill: { branchId: string; projectId: string; error: string } | null
  onResult: (a: Analysis) => void
}) {
  const projects = useSWR(keys.catalogProjects, listCatalogProjects)
  const [projectId, setProjectId] = React.useState("")
  const [branchId, setBranchId] = React.useState("")
  const [errorText, setErrorText] = React.useState("")
  const [pending, setPending] = React.useState(false)
  const [formError, setFormError] = React.useState<string | null>(null)

  const branches = useSWR(projectId ? keys.catalogBranches(projectId) : null, () => listCatalogBranches(projectId))

  // Auto-select when there is only one choice.
  React.useEffect(() => {
    if (!projectId && projects.data?.length === 1) setProjectId(projects.data[0].id)
  }, [projects.data, projectId])
  React.useEffect(() => {
    if (!branchId && branches.data?.length === 1) setBranchId(branches.data[0].id)
  }, [branches.data, branchId])

  React.useEffect(() => {
    if (!props.prefill) return
    setProjectId(props.prefill.projectId)
    setBranchId(props.prefill.branchId)
    setErrorText(props.prefill.error)
  }, [props.prefill])

  const tooLong = errorText.length > LIMITS.errorMessageChars
  const canSubmit = !props.disabled && !pending && branchId && errorText.trim() && !tooLong

  async function submit() {
    if (!canSubmit) return
    setPending(true)
    setFormError(null)
    try {
      const analysis = await analyzeSubmission(props.submissionId, {
        branch_id: branchId,
        error_message: errorText.trim(),
      })
      if (analysis.status === "success") toast.success("Fix found")
      else toast.warning("Analysis finished without a fix", { description: "See the details below." })
      props.onResult(analysis)
    } catch (err) {
      setFormError(errorMessage(err))
    } finally {
      setPending(false)
    }
  }

  const noReferences = projects.data && projects.data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <GitCompare className="size-4 text-emerald-400" />
          Compare against a reference
        </CardTitle>
        <CardDescription>
          Choose the reference solution this project should match, then paste the error you are seeing.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {projects.error ? (
          <ErrorState error={projects.error} onRetry={() => projects.mutate()} />
        ) : noReferences ? (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No reference projects are ready yet. An administrator needs to add one before you can run a
            comparison.
          </p>
        ) : (
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault()
              void submit()
            }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="project">Reference project</Label>
                <Select
                  value={projectId}
                  onValueChange={(v) => {
                    setProjectId(v)
                    setBranchId("")
                  }}
                  disabled={pending || !projects.data}
                >
                  <SelectTrigger id="project" className="w-full">
                    <SelectValue placeholder={projects.data ? "Select a project" : "Loading…"} />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.data?.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="branch">Branch</Label>
                <Select value={branchId} onValueChange={setBranchId} disabled={pending || !projectId || !branches.data}>
                  <SelectTrigger id="branch" className="w-full">
                    <SelectValue
                      placeholder={
                        !projectId ? "Pick a project first" : branches.isLoading ? "Loading…" : "Select a branch"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {branches.data?.map((b) => (
                      <SelectItem key={b.id} value={b.id}>
                        <span className="font-mono text-xs">{b.branch_name}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {branches.error && <p className="text-xs text-destructive">{errorMessage(branches.error)}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-end justify-between">
                <Label htmlFor="error-message">Error message or traceback</Label>
                <span className={cn("text-xs tabular-nums text-muted-foreground", tooLong && "text-destructive")}>
                  {errorText.length.toLocaleString()} / {LIMITS.errorMessageChars.toLocaleString()}
                </span>
              </div>
              <Textarea
                id="error-message"
                value={errorText}
                onChange={(e) => setErrorText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault()
                    void submit()
                  }
                }}
                placeholder={`Traceback (most recent call last):\n  File "app/routes/items.py", line 24, in get_item\n    return item.serialise()\nAttributeError: 'Item' object has no attribute 'serialise'`}
                className="min-h-40 font-mono text-xs"
                aria-invalid={tooLong}
                aria-describedby="error-hint"
                disabled={pending}
              />
              <p id="error-hint" className="text-xs text-muted-foreground">
                Paste the <strong>whole</strong> traceback, not just the last line — the file paths in it decide
                which of your files are analysed.
              </p>
            </div>

            {formError && (
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
                {formError}
              </p>
            )}

            <div className="flex flex-col-reverse items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted-foreground" aria-live="polite">
                {pending
                  ? "Comparing your code with the reference… this can take up to a minute."
                  : "Analyses are rate-limited per account."}
              </p>
              <Button type="submit" disabled={!canSubmit}>
                {pending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {pending ? "Analyzing…" : "Find the fix"}
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  )
}
