"use client"

import * as React from "react"
import useSWR from "swr"
import { toast } from "sonner"
import {
  CheckCircle2,
  Database,
  GitBranch,
  Loader2,
  RefreshCw,
  RotateCw,
  Server,
  Unlink,
  XCircle,
} from "lucide-react"
import { CopyButton, ErrorState, PageHeader, StatCard } from "@/components/app/common"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { errorMessage } from "@/lib/api/client"
import {
  getCollectionsHealth,
  getServerStatus,
  keys,
  listReferenceProjects,
  reindexReferenceProject,
} from "@/lib/api/endpoints"
import type { MissingCollection } from "@/lib/api/types"
import { cn } from "@/lib/utils"

export default function HealthPage() {
  const server = useSWR(keys.serverStatus, getServerStatus, { refreshInterval: 30000 })
  const health = useSWR(keys.health, getCollectionsHealth)
  const projects = useSWR(keys.referenceProjects, listReferenceProjects)

  const [lastChecked, setLastChecked] = React.useState<Date | null>(null)
  React.useEffect(() => {
    if (health.data) setLastChecked(new Date())
  }, [health.data])

  const refreshing = server.isValidating || health.isValidating
  const qdrantDown = health.data?.status === "error"
  const missing = health.data?.missing_collections ?? []
  const orphaned = health.data?.orphaned_collections ?? []
  const healthy = health.data?.status === "success" && missing.length === 0 && orphaned.length === 0

  // branch_id -> project_id, so a missing collection can be re-indexed in place.
  const projectOfBranch = React.useMemo(() => {
    const map = new Map<string, string>()
    for (const p of projects.data ?? []) for (const b of p.branches) map.set(b.id, p.id)
    return map
  }, [projects.data])

  function refresh() {
    void server.mutate()
    void health.mutate()
    void projects.mutate()
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="System health"
        description="Checks that the API is up and that every indexed branch still has its vector collection."
        actions={
          <Button variant="outline" onClick={refresh} disabled={refreshing}>
            <RefreshCw className={cn(refreshing && "animate-spin")} />
            Run checks
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="API server"
          icon={<Server className="size-4" />}
          value={
            server.isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : server.error ? (
              <StatusText ok={false}>Unreachable</StatusText>
            ) : (
              <StatusText ok>Online</StatusText>
            )
          }
          hint={server.error ? errorMessage(server.error) : server.data?.message}
        />
        <StatCard
          label="Vector store"
          icon={<Database className="size-4" />}
          value={
            health.isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : health.error || qdrantDown ? (
              <StatusText ok={false}>Unreachable</StatusText>
            ) : (
              <StatusText ok>Connected</StatusText>
            )
          }
          hint={lastChecked ? `Checked ${lastChecked.toLocaleTimeString()}` : undefined}
        />
        <StatCard
          label="Ready branches"
          icon={<GitBranch className="size-4" />}
          value={health.isLoading ? <Skeleton className="h-8 w-16" /> : qdrantDown ? "—" : `${health.data?.ready_branches ?? 0} / ${health.data?.total_branches ?? 0}`}
          hint="Indexed and visible to users"
        />
        <StatCard
          label="Issues found"
          icon={<Unlink className="size-4" />}
          value={health.isLoading ? <Skeleton className="h-8 w-10" /> : qdrantDown ? "—" : missing.length + orphaned.length}
          hint={healthy ? "Catalog and vector store agree" : "See details below"}
        />
      </div>

      {health.error ? (
        <ErrorState error={health.error} onRetry={() => health.mutate()} />
      ) : qdrantDown ? (
        <Alert variant="destructive">
          <XCircle className="size-4" />
          <AlertTitle>Could not reach the vector store</AlertTitle>
          <AlertDescription>{health.data?.message}</AlertDescription>
        </Alert>
      ) : healthy ? (
        <Alert className="border-emerald-200 bg-emerald-50/60 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
          <CheckCircle2 className="size-4 text-emerald-600" />
          <AlertTitle>Everything lines up</AlertTitle>
          <AlertDescription>Every ready branch has a collection, and there are no orphaned collections.</AlertDescription>
        </Alert>
      ) : health.data ? (
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <MissingCard
            items={missing}
            projectOfBranch={projectOfBranch}
            onQueued={() => {
              void health.mutate()
              void projects.mutate()
            }}
          />
          <OrphanedCard items={orphaned} />
        </div>
      ) : null}
    </div>
  )
}

function StatusText({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span className={cn("flex items-center gap-2 text-lg", ok ? "text-emerald-700 dark:text-emerald-400" : "text-destructive")}>
      <span className={cn("size-2 rounded-full", ok ? "bg-emerald-500" : "bg-destructive")} aria-hidden="true" />
      {children}
    </span>
  )
}

function MissingCard(props: {
  items: MissingCollection[]
  projectOfBranch: Map<string, string>
  onQueued: () => void
}) {
  const [busy, setBusy] = React.useState<string | null>(null)

  async function reindex(item: MissingCollection) {
    const projectId = props.projectOfBranch.get(item.branch_id)
    if (!projectId) {
      toast.error("Could not find the project for this branch. Refresh and try again.")
      return
    }
    setBusy(item.branch_id)
    try {
      const res = await reindexReferenceProject(projectId, item.branch_name)
      toast.success("Re-index queued", { description: res.message })
      props.onQueued()
    } catch (err) {
      toast.error("Could not start re-indexing", { description: errorMessage(err) })
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Missing collections ({props.items.length})</CardTitle>
        <CardDescription>
          Branches marked ready whose vector collection no longer exists. Users can pick them but analyses will
          fail — re-index to rebuild.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {props.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">None.</p>
        ) : (
          <ul className="divide-y rounded-md border">
            {props.items.map((m) => (
              <li key={m.branch_id} className="flex items-center gap-3 p-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-mono text-sm">{m.branch_name}</div>
                  <div className="truncate font-mono text-xs text-muted-foreground">{m.collection_name}</div>
                </div>
                <Button size="sm" variant="outline" onClick={() => reindex(m)} disabled={busy === m.branch_id}>
                  {busy === m.branch_id ? <Loader2 className="animate-spin" /> : <RotateCw />}
                  Re-index
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function OrphanedCard({ items }: { items: string[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Orphaned collections ({items.length})</CardTitle>
        <CardDescription>
          Collections with no owning branch, usually left behind by a failed delete. They are safe to drop
          directly in Qdrant.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">None.</p>
        ) : (
          <ul className="divide-y rounded-md border">
            {items.map((name) => (
              <li key={name} className="flex items-center gap-2 p-3">
                <span className="min-w-0 flex-1 truncate font-mono text-xs">{name}</span>
                <CopyButton value={name} label="Copy collection name" />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
