import type React from "react"
import Link from "next/link"
import {
  ArrowRight,
  CheckCircle2,
  ClipboardPaste,
  FolderGit2,
  FolderUp,
  GitCompare,
  History,
  Lightbulb,
  Lock,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Wand2,
} from "lucide-react"
import { Brand } from "@/components/brand"
import { RetrievalGraph } from "@/components/retrieval-graph"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function Page() {
  return (
    <div className="relative">
      <SiteHeader />
      <Hero />
      <Audiences />
      <HowItWorks />
      <ResultsPreview />
      <CTA />
      <LandingFooter />
    </div>
  )
}

function Hero() {
  return (
    <section className="relative isolate overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(50%_55%_at_72%_32%,rgb(16_185_129/0.18),transparent_70%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-20 bg-[linear-gradient(to_right,rgb(255_255_255/0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgb(255_255_255/0.04)_1px,transparent_1px)] bg-[size:56px_56px] [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]"
      />

      <div className="relative">
        <RetrievalGraph className="pointer-events-none absolute inset-0 -z-10 opacity-40 md:opacity-100" />
        <div className="container mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-4 pb-16 pt-12 md:grid-cols-[1.15fr_1fr] md:pb-20 md:pt-14">
          <div className="max-w-xl space-y-7 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-4 motion-safe:duration-700">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-300">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full rounded-full bg-emerald-400 opacity-75 motion-safe:animate-ping" />
                <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
              </span>
              Retrieval‑augmented debugging
            </div>
            <h1 className="text-balance text-5xl font-bold tracking-tight sm:text-6xl">
              Paste your error. Get the{" "}
              <span className="bg-gradient-to-r from-emerald-300 to-teal-200 bg-clip-text text-transparent">
                exact line
              </span>{" "}
              to change.
            </h1>
            <p className="text-pretty text-lg leading-relaxed text-muted-foreground">
              Upload your project, pick the reference solution it should match, and paste the traceback. We compare
              your code with the working version and tell you which file, which line, and what to replace it with.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg" className="font-semibold">
                <Link href="/register">
                  <FolderUp />
                  Get started — it&apos;s free
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/login">I already have an account</Link>
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
              <Point>Upload a folder or a .zip</Point>
              <Point>node_modules &amp; .venv skipped</Point>
              <Point>Every attempt saved</Point>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto max-w-5xl px-4 pb-16 md:pb-20">
        <HeroPreview />
      </div>
    </section>
  )
}

function HeroPreview() {
  return (
    <div className="relative motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-6 motion-safe:delay-150 motion-safe:duration-700 motion-safe:fill-mode-both">
      <div
        aria-hidden="true"
        className="absolute -inset-px rounded-xl bg-gradient-to-b from-emerald-400/40 via-white/10 to-transparent"
      />
      <div className="relative overflow-hidden rounded-xl bg-background/90 shadow-2xl shadow-emerald-950/50 backdrop-blur">
        <div className="flex items-center gap-4 border-b px-4 py-3">
          <div className="flex gap-1.5" aria-hidden="true">
            <span className="size-3 rounded-full bg-white/15" />
            <span className="size-3 rounded-full bg-white/15" />
            <span className="size-3 rounded-full bg-white/15" />
          </div>
          <span className="truncate font-mono text-xs text-muted-foreground">analysis · app/routes/items.py</span>
          <span className="ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
            <CheckCircle2 className="size-3.5" />
            Fix found
          </span>
        </div>

        <div className="grid divide-y md:grid-cols-2 md:divide-x md:divide-y-0">
          <div className="p-5">
            <PaneLabel icon={<ClipboardPaste className="size-4" />}>Your traceback</PaneLabel>
            <pre className="mt-3 whitespace-pre-wrap break-words font-mono text-sm leading-7 text-muted-foreground">
              {`Traceback (most recent call last):
  File "app/routes/items.py", line 24
    return item.serialise()
`}
              <span className="text-red-400">AttributeError: &apos;Item&apos; object has no attribute &apos;serialise&apos;</span>
            </pre>
          </div>

          <div className="space-y-4 p-5">
            <PaneLabel icon={<Wand2 className="size-4" />}>Suggested fix</PaneLabel>
            <p className="text-sm leading-relaxed">
              The method is spelled <code className="font-mono text-emerald-300">serialize</code>, not{" "}
              <code className="font-mono text-red-300">serialise</code>. The reference solution calls it the same way
              on this line.
            </p>
            <div className="overflow-hidden rounded-lg border font-mono text-sm">
              <div className="flex justify-between border-b px-3 py-2 text-xs text-muted-foreground">
                <span>app/routes/items.py</span>
                <span>line 24</span>
              </div>
              <div className="bg-red-500/10 px-3 py-1.5 text-red-300">- return item.serialise()</div>
              <div className="bg-emerald-500/10 px-3 py-1.5 text-emerald-300">+ return item.serialize()</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function PaneLabel({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
      <span className="text-emerald-400">{icon}</span>
      {children}
    </div>
  )
}

function Point({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <CheckCircle2 className="size-4 text-emerald-500" />
      {children}
    </div>
  )
}

function Audiences() {
  return (
    <section className="container mx-auto max-w-6xl px-4 py-16">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold tracking-tight">Built for learners, curated by admins</h2>
        <p className="mt-3 text-muted-foreground">
          Administrators decide which reference solutions are available. Everyone else helps themselves.
        </p>
      </div>

      <div className="mt-10 grid items-stretch gap-6 md:grid-cols-2">
        <AudienceCard
          icon={<UploadCloud className="size-5 text-emerald-400" />}
          title="For learners"
          description="Self‑service, no waiting on anyone."
          points={[
            "Create an account and upload up to 5 projects",
            "Choose which reference and branch to compare against",
            "Get a fix with the file, line, and exact replacement",
            "Review every past attempt, including failed ones",
          ]}
          cta={
            <Button asChild size="lg" className="w-full">
              <Link href="/register">
                <FolderUp />
                Create a free account
              </Link>
            </Button>
          }
        />
        <AudienceCard
          icon={<FolderGit2 className="size-5 text-emerald-400" />}
          title="For administrators"
          description="Curate references and keep the system healthy."
          points={[
            "Add a Git repository — every branch is indexed",
            "Watch indexing progress and retry failed branches",
            "Reconcile the catalog against the vector store",
            "Manage accounts and grant admin access",
          ]}
          cta={
            <Button asChild size="lg" variant="outline" className="w-full">
              <Link href="/login">
                <ShieldCheck />
                Sign in to the admin area
              </Link>
            </Button>
          }
        />
      </div>
    </section>
  )
}

function AudienceCard(props: {
  icon: React.ReactNode
  title: string
  description: string
  points: string[]
  cta: React.ReactNode
}) {
  return (
    <Card className="flex h-full flex-col border-emerald-500/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {props.icon}
          {props.title}
        </CardTitle>
        <CardDescription>{props.description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-6">
        <ul className="space-y-3">
          {props.points.map((p, i) => (
            <li key={p} className="flex items-start gap-3">
              <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-emerald-300">
                {i + 1}
              </span>
              <span className="text-sm">{p}</span>
            </li>
          ))}
        </ul>
        {props.cta}
      </CardContent>
    </Card>
  )
}

function HowItWorks() {
  const steps = [
    { icon: <FolderUp className="size-5 text-emerald-400" />, title: "Upload", desc: "Pick your project folder or a .zip. Build artefacts are skipped." },
    { icon: <GitCompare className="size-5 text-emerald-400" />, title: "Pick a reference", desc: "Choose the working solution and branch your code should match." },
    { icon: <ClipboardPaste className="size-5 text-emerald-400" />, title: "Paste the error", desc: "Include the full traceback — its file paths guide the analysis." },
    { icon: <Sparkles className="size-5 text-emerald-400" />, title: "Apply the fix", desc: "Copy the replacement straight into the file and line shown." },
  ]
  return (
    <section id="how-it-works" className="bg-gradient-to-b from-slate-50 to-white py-16 dark:from-card dark:to-background">
      <div className="container mx-auto px-4">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-3xl font-bold tracking-tight">How it works</h2>
          <p className="mt-3 text-muted-foreground">From upload to fix in a couple of minutes.</p>
        </div>
        <ol className="mx-auto mt-10 grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-4">
          {steps.map((s, i) => (
            <li key={s.title}>
              <Card className="h-full">
                <CardHeader className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="inline-flex size-9 items-center justify-center rounded-md bg-emerald-50 dark:bg-emerald-950">
                      {s.icon}
                    </div>
                    <span className="text-xs font-medium text-muted-foreground">Step {i + 1}</span>
                  </div>
                  <CardTitle className="text-base">{s.title}</CardTitle>
                  <CardDescription>{s.desc}</CardDescription>
                </CardHeader>
              </Card>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

function ResultsPreview() {
  const features = [
    { icon: <Lightbulb className="size-5 text-emerald-400" />, title: "A plain‑language explanation", desc: "Why the error happens, not just where." },
    { icon: <GitCompare className="size-5 text-emerald-400" />, title: "Before and after", desc: "The exact code to replace, with one‑click copy." },
    { icon: <History className="size-5 text-emerald-400" />, title: "Full history", desc: "Every attempt is saved so you can compare approaches." },
    { icon: <Lock className="size-5 text-emerald-400" />, title: "Private by default", desc: "Only you — and administrators — can see your uploads." },
  ]
  return (
    <section className="container mx-auto max-w-5xl px-4 py-16">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold tracking-tight">Results designed for action</h2>
        <p className="mt-3 text-muted-foreground">No wall of text. Just what to change and why.</p>
      </div>
      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        {features.map((f) => (
          <div key={f.title} className="flex gap-4 rounded-lg border p-5">
            <div className="inline-flex size-9 shrink-0 items-center justify-center rounded-md bg-emerald-50 dark:bg-emerald-950">
              {f.icon}
            </div>
            <div>
              <div className="font-medium">{f.title}</div>
              <div className="mt-1 text-sm text-muted-foreground">{f.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function CTA() {
  return (
    <section className="container mx-auto px-4 pb-16">
      <div className="relative overflow-hidden rounded-xl border border-emerald-500/25 bg-gradient-to-br from-emerald-500/15 via-card to-card p-8">
        <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-emerald-500/20 blur-3xl" />
        <div className="relative grid items-center gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-2xl font-semibold">Stuck on an error right now?</h3>
            <p className="mt-2 text-muted-foreground">Create an account and have a fix in front of you in minutes.</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
            <Button asChild size="lg" className="font-semibold">
              <Link href="/register">
                Get started
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

function LandingFooter() {
  return (
    <footer className="border-t">
      <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-muted-foreground md:flex-row">
        <Brand className="text-foreground" />
        <nav className="flex items-center gap-4" aria-label="Footer">
          <Link href="/how-it-works" className="hover:text-foreground">
            How it works
          </Link>
          <Link href="/faq" className="hover:text-foreground">
            FAQ
          </Link>
          <Link href="/login" className="hover:text-foreground">
            Sign in
          </Link>
        </nav>
      </div>
    </footer>
  )
}
