"use client"

import * as React from "react"
import { AlertTriangle, Check, CheckCircle2, Clock, Copy, Loader2, RefreshCw, XCircle } from "lucide-react"
import { toast } from "sonner"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { errorMessage } from "@/lib/api/client"
import type { AnalysisStatus, BranchStatus } from "@/lib/api/types"
import { cn } from "@/lib/utils"

export function PageHeader(props: {
  title: string
  description?: React.ReactNode
  actions?: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 space-y-1">
        <h1 className="truncate text-2xl font-semibold tracking-tight">{props.title}</h1>
        {props.description && <p className="text-sm text-muted-foreground">{props.description}</p>}
      </div>
      {props.actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{props.actions}</div>}
    </div>
  )
}

export function EmptyState(props: {
  icon: React.ReactNode
  title: string
  description?: React.ReactNode
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center",
        props.className,
      )}
    >
      <div className="mb-4 inline-flex size-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950">
        {props.icon}
      </div>
      <h3 className="font-medium">{props.title}</h3>
      {props.description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{props.description}</p>
      )}
      {props.action && <div className="mt-6">{props.action}</div>}
    </div>
  )
}

export function ErrorState(props: { error: unknown; onRetry?: () => void; title?: string }) {
  return (
    <Alert variant="destructive">
      <AlertTriangle className="size-4" />
      <AlertTitle>{props.title ?? "Could not load this data"}</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3">
        <span>{errorMessage(props.error)}</span>
        {props.onRetry && (
          <Button size="sm" variant="outline" onClick={props.onRetry}>
            <RefreshCw />
            Try again
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}

export function StatCard(props: {
  label: string
  value: React.ReactNode
  hint?: React.ReactNode
  icon?: React.ReactNode
  children?: React.ReactNode
}) {
  return (
    <Card className="py-0">
      <CardContent className="space-y-1 p-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{props.label}</span>
          {props.icon}
        </div>
        <div className="text-2xl font-semibold tabular-nums">{props.value}</div>
        {props.hint && <div className="text-xs text-muted-foreground">{props.hint}</div>}
        {props.children}
      </CardContent>
    </Card>
  )
}

const BRANCH_STATUS: Record<BranchStatus, { label: string; className: string; icon: React.ReactNode }> = {
  pending: {
    label: "Queued",
    className: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300",
    icon: <Clock className="size-3" />,
  },
  indexing: {
    label: "Indexing",
    className: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300",
    icon: <Loader2 className="size-3 animate-spin" />,
  },
  ready: {
    label: "Ready",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300",
    icon: <CheckCircle2 className="size-3" />,
  },
  failed: {
    label: "Failed",
    className: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300",
    icon: <XCircle className="size-3" />,
  },
}

export function BranchStatusBadge({ status }: { status: BranchStatus }) {
  const s = BRANCH_STATUS[status]
  return (
    <Badge variant="outline" className={cn("gap-1 font-medium", s.className)}>
      {s.icon}
      {s.label}
    </Badge>
  )
}

export function AnalysisStatusBadge({ status }: { status: AnalysisStatus }) {
  return status === "success" ? (
    <Badge variant="outline" className={cn("gap-1", BRANCH_STATUS.ready.className)}>
      <CheckCircle2 className="size-3" />
      Fix found
    </Badge>
  ) : (
    <Badge variant="outline" className={cn("gap-1", BRANCH_STATUS.failed.className)}>
      <XCircle className="size-3" />
      Failed
    </Badge>
  )
}

/**
 * Confirmation for destructive or privileged actions. Stays open while the
 * action runs so the user sees progress; the caller surfaces errors.
 */
export function ConfirmDialog(props: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: React.ReactNode
  confirmLabel: string
  destructive?: boolean
  onConfirm: () => Promise<void>
}) {
  const [pending, setPending] = React.useState(false)

  async function run(e: React.MouseEvent) {
    e.preventDefault()
    setPending(true)
    try {
      await props.onConfirm()
      props.onOpenChange(false)
    } catch {
      // The caller already surfaced the error; staying open lets the user retry.
    } finally {
      setPending(false)
    }
  }

  return (
    <AlertDialog open={props.open} onOpenChange={(o) => !pending && props.onOpenChange(o)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{props.title}</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 text-sm text-muted-foreground">{props.description}</div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={run}
            disabled={pending}
            className={cn(
              props.destructive
                ? "bg-destructive text-white hover:bg-destructive/90"
                : "bg-emerald-600 text-white hover:bg-emerald-700",
            )}
          >
            {pending && <Loader2 className="animate-spin" />}
            {props.confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = React.useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error("Could not copy to clipboard")
    }
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="size-7 text-muted-foreground hover:text-foreground"
          onClick={copy}
          aria-label={label}
        >
          {copied ? <Check className="size-3.5 text-emerald-600" /> : <Copy className="size-3.5" />}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{copied ? "Copied" : label}</TooltipContent>
    </Tooltip>
  )
}
