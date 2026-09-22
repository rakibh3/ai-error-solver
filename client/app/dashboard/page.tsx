"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import useSWR from "swr"
import { toast } from "sonner"
import {
  ChevronRight,
  FileCode2,
  FolderGit2,
  FolderUp,
  GitBranch,
  HardDrive,
  Library,
  MoreHorizontal,
  Plus,
  Trash2,
} from "lucide-react"
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  PageHeader,
  StatCard,
} from "@/components/app/common"
import { UploadDialog } from "@/components/app/upload-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { useSession } from "@/hooks/use-session"
import { errorMessage } from "@/lib/api/client"
import {
  deleteSubmission,
  keys,
  listCatalogBranches,
  listCatalogProjects,
  listSubmissions,
} from "@/lib/api/endpoints"
import type { CatalogProject, Submission } from "@/lib/api/types"
import { LIMITS, formatBytes, formatDateTime, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"

export default function DashboardPage() {
  const router = useRouter()
  const { user, isAdmin } = useSession()
  const submissions = useSWR(keys.submissions, listSubmissions)
  const catalog = useSWR(keys.catalogProjects, listCatalogProjects)

  const [uploadOpen, setUploadOpen] = React.useState(false)
  const [toDelete, setToDelete] = React.useState<Submission | null>(null)

  // Admins receive every account's submissions; quota applies to your own.
  const own = React.useMemo(
    () => (submissions.data ?? []).filter((s) => s.owner_id === user?.id),
    [submissions.data, user?.id],
  )
  const usedBytes = own.reduce((sum, s) => sum + s.total_bytes, 0)
  const quotaReached = own.length >= LIMITS.submissionQuota

  async function confirmDelete() {
    if (!toDelete) return
    try {
      await deleteSubmission(toDelete.id)
      toast.success("Submission deleted", { description: `“${toDelete.display_name}” and its analyses were removed.` })
      await submissions.mutate((list) => list?.filter((s) => s.id !== toDelete.id), { revalidate: true })
    } catch (err) {
      toast.error("Could not delete submission", { description: errorMessage(err) })
      throw err
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title={isAdmin ? "All submissions" : "Your submissions"}
        description={
          isAdmin
            ? "As an administrator you can see and manage submissions from every account."
            : "Upload a project, then compare it against a reference to get a targeted fix."
        }
        actions={
          <Button
            onClick={() => setUploadOpen(true)}
            disabled={quotaReached}
            title={quotaReached ? "Delete a submission to free up a slot" : undefined}
          >
            <Plus />
            Upload project
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Submission slots"
          icon={<FolderUp className="size-4" />}
          value={
            submissions.isLoading ? <Skeleton className="h-8 w-16" /> : `${own.length} / ${LIMITS.submissionQuota}`
          }
          hint={quotaReached ? "Limit reached — delete one to upload again" : "Your own uploads"}
        >
          <Progress value={(own.length / LIMITS.submissionQuota) * 100} className="mt-2 h-1.5" />
        </StatCard>
        <StatCard
          label="Storage used"
          icon={<HardDrive className="size-4" />}
          value={submissions.isLoading ? <Skeleton className="h-8 w-20" /> : formatBytes(usedBytes)}
          hint={`of ${formatBytes(LIMITS.storageQuotaBytes)}`}
        >
          <Progress value={(usedBytes / LIMITS.storageQuotaBytes) * 100} className="mt-2 h-1.5" />
        </StatCard>
        <StatCard
          label="References available"
          icon={<Library className="size-4" />}
          value={catalog.isLoading ? <Skeleton className="h-8 w-10" /> : (catalog.data?.length ?? 0)}
          hint="Projects you can compare against"
        />
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-3">
        <section className="space-y-3 lg:col-span-2" aria-labelledby="submissions-heading">
          <h2 id="submissions-heading" className="sr-only">
            Submissions
          </h2>
          {submissions.error ? (
            <ErrorState error={submissions.error} onRetry={() => submissions.mutate()} />
          ) : submissions.isLoading ? (
            <SubmissionSkeleton />
          ) : !submissions.data?.length ? (
            <EmptyState
              icon={<FolderUp className="size-6" />}
              title="No submissions yet"
              description="Upload your project folder or a .zip. You can then pick a reference and paste the error you're seeing."
              action={
                <Button onClick={() => setUploadOpen(true)}>
                  <Plus />
                  Upload your first project
                </Button>
              }
            />
          ) : (
            <ul className="space-y-3">
              {submissions.data.map((s) => (
                <SubmissionRow
                  key={s.id}
                  submission={s}
                  mine={s.owner_id === user?.id}
                  showOwner={isAdmin}
                  onDelete={() => setToDelete(s)}
                />
              ))}
            </ul>
          )}
        </section>

        <ReferenceLibrary projects={catalog.data} isLoading={catalog.isLoading} error={catalog.error} onRetry={() => catalog.mutate()} />
      </div>

      <UploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUploaded={(s) => {
          setUploadOpen(false)
          toast.success("Upload complete", {
            description: `${s.file_count} files stored. Next, pick a reference and describe your error.`,
          })
          void submissions.mutate()
          router.push(`/dashboard/submissions/${s.id}`)
        }}
      />

      <ConfirmDialog
        open={Boolean(toDelete)}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this submission?"
        description={
          <>
            <p>
              “{toDelete?.display_name}” will be permanently removed, along with its files and its entire
              analysis history. This frees up the slot and storage it was using.
            </p>
            <p className="font-medium text-foreground">This cannot be undone.</p>
          </>
        }
        confirmLabel="Delete submission"
        destructive
        onConfirm={confirmDelete}
      />
    </div>
  )
}

function SubmissionRow(props: {
  submission: Submission
  mine: boolean
  showOwner: boolean
  onDelete: () => void
}) {
  const s = props.submission
  const href = `/dashboard/submissions/${s.id}`
  return (
    <li>
      <Card className="group relative py-0 transition-colors hover:border-emerald-500/50">
        <CardContent className="flex items-center gap-4 p-4">
          <div className="hidden size-10 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-emerald-700 sm:flex dark:bg-emerald-950 dark:text-emerald-300">
            <FileCode2 className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Link
                href={href}
                className="truncate font-medium after:absolute after:inset-0 focus-visible:outline-none"
              >
                {s.display_name}
              </Link>
              {props.showOwner && (
                <Badge variant="outline" className="shrink-0 font-normal">
                  {props.mine ? "Yours" : `User #${s.owner_id}`}
                </Badge>
              )}
            </div>
            <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span>{s.file_count.toLocaleString()} files</span>
              <span>{formatBytes(s.total_bytes)}</span>
              <time dateTime={s.created_at} title={formatDateTime(s.created_at)}>
                Uploaded {timeAgo(s.created_at)}
              </time>
            </div>
          </div>
          <div className="relative z-10 flex items-center gap-1">
            <Button asChild size="sm" variant="outline" className="hidden sm:inline-flex">
              <Link href={href}>Analyze</Link>
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="icon" variant="ghost" aria-label={`Actions for ${s.display_name}`}>
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href={href}>
                    <ChevronRight />
                    Open
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem variant="destructive" onSelect={props.onDelete}>
                  <Trash2 />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>
    </li>
  )
}

function SubmissionSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-[74px] w-full rounded-xl" />
      ))}
    </div>
  )
}

function ReferenceLibrary(props: {
  projects: CatalogProject[] | undefined
  isLoading: boolean
  error: unknown
  onRetry: () => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Library className="size-4 text-emerald-400" />
          Reference library
        </CardTitle>
        <CardDescription>Working solutions curated by administrators. Expand one to see its branches.</CardDescription>
      </CardHeader>
      <CardContent>
        {props.error ? (
          <ErrorState error={props.error} onRetry={props.onRetry} />
        ) : props.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : !props.projects?.length ? (
          <p className="text-sm text-muted-foreground">
            No references are ready yet. An administrator needs to add and index one before you can run a
            comparison.
          </p>
        ) : (
          <ul className="-mx-2 space-y-1">
            {props.projects.map((p) => (
              <ReferenceItem key={p.id} project={p} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function ReferenceItem({ project }: { project: CatalogProject }) {
  const [open, setOpen] = React.useState(false)
  const branches = useSWR(open ? keys.catalogBranches(project.id) : null, () => listCatalogBranches(project.id))

  return (
    <li>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500">
          <ChevronRight className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-90")} />
          <FolderGit2 className="size-4 shrink-0 text-emerald-400" />
          <span className="min-w-0 flex-1 truncate font-medium">{project.name}</span>
          <Badge variant="secondary" className="shrink-0 tabular-nums">
            {project.ready_branch_count}
          </Badge>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="ml-8 mt-1 space-y-1 border-l pl-3">
            {branches.isLoading ? (
              <Skeleton className="h-5 w-32" />
            ) : branches.error ? (
              <p className="text-xs text-destructive">{errorMessage(branches.error)}</p>
            ) : (
              branches.data?.map((b) => (
                <div key={b.id} className="flex items-center gap-2 py-0.5 text-xs">
                  <GitBranch className="size-3 text-muted-foreground" />
                  <span className="truncate font-mono">{b.branch_name}</span>
                  <span className="ml-auto shrink-0 text-muted-foreground">{timeAgo(b.indexed_at)}</span>
                </div>
              ))
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </li>
  )
}
