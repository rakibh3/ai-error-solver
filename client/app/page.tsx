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
import { SiteHeader } from "@/components/site-header"
import { Badge } from "@/components/ui/badge"
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
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-1/2 top-[-6rem] -z-10 h-[30rem] w-[50rem] -translate-x-1/2 rounded-full bg-gradient-to-b from-emerald-200/60 to-transparent blur-3xl" />
      <div className="container mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-4 py-16 md:grid-cols-2 md:py-24">
        <div className="space-y-6">
          <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">AI‑powered error solving</Badge>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Paste your error. Get the exact line to change.
          </h1>
          <p className="text-lg text-muted-foreground">
            Upload your project, pick the reference solution it should match, and paste the traceback. We compare
            your code with the working version and tell you which file, which line, and what to replace it with.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="bg-emerald-600 hover:bg-emerald-700">
              <Link href="/register">
                <FolderUp />
                Get started — it&apos;s free
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/login">I already have an account</Link>
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-4 pt-2 text-sm text-muted-foreground">
            <Point>Upload a folder or a .zip</Point>
            <Point>node_modules &amp; .venv skipped</Point>
            <Point>Every attempt saved</Point>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -left-10 -top-10 size-24 rounded-full bg-emerald-200/60 blur-2xl" />
          <Card className="relative overflow-hidden">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wand2 className="size-5 text-emerald-600" />
                What you&apos;ll get back
              </CardTitle>
              <CardDescription>A real result, in the shape the app shows it.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 text-sm">
                <Lightbulb className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                <span className="text-muted-foreground">
                  The method is spelled <code className="font-mono">serialize</code>, not{" "}
                  <code className="font-mono">serialise</code>.
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                Change in <code className="rounded bg-muted px-1.5 py-0.5 font-mono">app/routes/items.py:24</code>
              </div>
              <div className="grid gap-2 text-xs sm:grid-cols-2">
                <pre className="overflow-auto rounded-md border border-red-200 bg-slate-950 p-3 text-red-200">
                  - return item.serialise()
                </pre>
                <pre className="overflow-auto rounded-md border border-emerald-200 bg-slate-950 p-3 text-emerald-200">
                  + return item.serialize()
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}

function Point({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <CheckCircle2 className="size-4 text-emerald-600" />
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
          icon={<UploadCloud className="size-5 text-emerald-600" />}
          title="For learners"
          description="Self‑service, no waiting on anyone."
          points={[
            "Create an account and upload up to 5 projects",
            "Choose which reference and branch to compare against",
            "Get a fix with the file, line, and exact replacement",
            "Review every past attempt, including failed ones",
          ]}
          cta={
            <Button asChild size="lg" className="w-full bg-emerald-600 hover:bg-emerald-700">
              <Link href="/register">
                <FolderUp />
                Create a free account
              </Link>
            </Button>
          }
        />
        <AudienceCard
          icon={<FolderGit2 className="size-5 text-emerald-600" />}
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
    <Card className="flex h-full flex-col border-emerald-200/60">
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
              <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-xs font-semibold text-white">
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
    { icon: <FolderUp className="size-5 text-emerald-600" />, title: "Upload", desc: "Pick your project folder or a .zip. Build artefacts are skipped." },
    { icon: <GitCompare className="size-5 text-emerald-600" />, title: "Pick a reference", desc: "Choose the working solution and branch your code should match." },
    { icon: <ClipboardPaste className="size-5 text-emerald-600" />, title: "Paste the error", desc: "Include the full traceback — its file paths guide the analysis." },
    { icon: <Sparkles className="size-5 text-emerald-600" />, title: "Apply the fix", desc: "Copy the replacement straight into the file and line shown." },
  ]
  return (
    <section id="how-it-works" className="bg-gradient-to-b from-slate-50 to-white py-16 dark:from-slate-950 dark:to-background">
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
    { icon: <Lightbulb className="size-5 text-emerald-600" />, title: "A plain‑language explanation", desc: "Why the error happens, not just where." },
    { icon: <GitCompare className="size-5 text-emerald-600" />, title: "Before and after", desc: "The exact code to replace, with one‑click copy." },
    { icon: <History className="size-5 text-emerald-600" />, title: "Full history", desc: "Every attempt is saved so you can compare approaches." },
    { icon: <Lock className="size-5 text-emerald-600" />, title: "Private by default", desc: "Only you — and administrators — can see your uploads." },
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
      <div className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-emerald-600 via-emerald-700 to-emerald-800 p-8 text-white">
        <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-emerald-400/30 blur-2xl" />
        <div className="absolute -bottom-10 -left-10 h-48 w-48 rounded-full bg-emerald-400/30 blur-2xl" />
        <div className="relative grid items-center gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-2xl font-semibold">Stuck on an error right now?</h3>
            <p className="mt-2 text-emerald-100">Create an account and have a fix in front of you in minutes.</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
            <Button asChild size="lg" variant="secondary" className="text-emerald-900">
              <Link href="/register">
                Get started
                <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="secondary" className="bg-white/10 text-white hover:bg-white/20">
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
