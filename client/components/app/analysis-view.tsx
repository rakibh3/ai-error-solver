"use client"

import * as React from "react"
import { AlertTriangle, Bot, FileCode2, Lightbulb, Minus, Plus } from "lucide-react"
import { AnalysisStatusBadge, CopyButton } from "@/components/app/common"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import type { Analysis } from "@/lib/api/types"
import { formatDateTime } from "@/lib/format"
import { cn } from "@/lib/utils"

/** Full rendering of one analysis: explanation, location, and the before/after change. */
export function AnalysisResultView({ analysis }: { analysis: Analysis }) {
  if (analysis.status === "failed" || !analysis.result) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="size-4" />
        <AlertTitle>The model could not produce a usable fix</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>{analysis.failure_reason ?? "No reason was given."}</p>
          <p className="text-muted-foreground">
            This attempt was still saved to your history. Try again with the full traceback, or compare
            against a different reference branch.
          </p>
        </AlertDescription>
      </Alert>
    )
  }

  const { error_explanation, fix_instructions: fix } = analysis.result
  const location = fix.file ? `${fix.file}${fix.line ? `:${fix.line}` : ""}` : null

  return (
    <div className="space-y-5">
      <div className="flex gap-3 rounded-lg border border-emerald-200 bg-emerald-50/60 p-4 dark:border-emerald-900 dark:bg-emerald-950/30">
        <Lightbulb className="mt-0.5 size-5 shrink-0 text-emerald-400" />
        <div className="space-y-1">
          <div className="text-sm font-medium">What went wrong</div>
          <p className="text-sm leading-relaxed text-muted-foreground">{error_explanation}</p>
        </div>
      </div>

      {location && (
        <div className="flex items-center gap-2 text-sm">
          <FileCode2 className="size-4 text-muted-foreground" />
          <span className="text-muted-foreground">Change in</span>
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{location}</code>
          <CopyButton value={location} label="Copy file path" />
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <CodeBlock tone="remove" title="Replace this" code={fix.change.old_code} />
        <CodeBlock tone="add" title="With this" code={fix.change.new_code} />
      </div>
    </div>
  )
}

function CodeBlock(props: { tone: "add" | "remove"; title: string; code: string }) {
  const empty = !props.code.trim()
  const Icon = props.tone === "add" ? Plus : Minus
  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border",
        props.tone === "add"
          ? "border-emerald-200 dark:border-emerald-900"
          : "border-red-200 dark:border-red-900",
      )}
    >
      <div
        className={cn(
          "flex items-center justify-between px-3 py-1.5 text-xs font-medium",
          props.tone === "add"
            ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
            : "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300",
        )}
      >
        <span className="flex items-center gap-1.5">
          <Icon className="size-3.5" />
          {props.title}
        </span>
        {!empty && <CopyButton value={props.code} label={`Copy “${props.title.toLowerCase()}”`} />}
      </div>
      <pre className="max-h-80 overflow-auto bg-slate-950 p-3 text-xs leading-relaxed text-slate-100">
        <code>{empty ? (props.tone === "add" ? "(remove it — no replacement needed)" : "(add new code — nothing to replace)") : props.code}</code>
      </pre>
    </div>
  )
}

export function AnalysisMeta({ analysis, branchLabel }: { analysis: Analysis; branchLabel: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <AnalysisStatusBadge status={analysis.status} />
      <span>vs. {branchLabel}</span>
      <span className="flex items-center gap-1">
        <Bot className="size-3" />
        {analysis.model}
      </span>
      <time dateTime={analysis.created_at}>{formatDateTime(analysis.created_at)}</time>
    </div>
  )
}
