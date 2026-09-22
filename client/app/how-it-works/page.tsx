import Link from "next/link"
import { SiteHeader } from "@/components/site-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Activity,
  ClipboardPaste,
  FolderGit2,
  FolderUp,
  GitCompare,
  RotateCw,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react"

export default function HowItWorksPage() {
  return (
    <main>
      <SiteHeader />
      <section className="bg-gradient-to-b from-slate-50 to-white py-12 md:py-16 dark:from-card dark:to-background">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="mb-8 flex items-center gap-2">
            <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/15">Guide</Badge>
            <span className="text-muted-foreground">From upload to fix in minutes</span>
          </div>

          <h2 className="mb-4 text-xl font-semibold">Getting a fix</h2>
          <div className="grid gap-6 md:grid-cols-4">
            <Step icon={<FolderUp className="size-5 text-emerald-400" />} title="1. Upload" desc="Choose your project folder or a .zip. It is compressed in your browser, and build folders are skipped." />
            <Step icon={<GitCompare className="size-5 text-emerald-400" />} title="2. Pick a reference" desc="Select the reference project and branch that contains the working version of your task." />
            <Step icon={<ClipboardPaste className="size-5 text-emerald-400" />} title="3. Paste the error" desc="Paste the entire traceback. File paths in it decide which of your files are analysed." />
            <Step icon={<Sparkles className="size-5 text-emerald-400" />} title="4. Apply the fix" desc="Get an explanation plus the file, line, and exact code to replace — ready to copy." />
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Behind the scenes</CardTitle>
                <CardDescription>Why the answer points at a specific line.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm">
                <Point icon={<FolderGit2 className="size-4 text-emerald-400" />} title="Indexed references" desc="Each reference branch is split into searchable chunks when an administrator adds it." />
                <Point icon={<GitCompare className="size-4 text-emerald-400" />} title="Targeted comparison" desc="Your files named in the traceback are matched with the most similar reference code." />
                <Point icon={<ShieldCheck className="size-4 text-emerald-400" />} title="Validated output" desc="The model's answer is checked against a strict format before it is shown to you." />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">For administrators</CardTitle>
                <CardDescription>Keeping the reference library useful.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm">
                <Point icon={<FolderGit2 className="size-4 text-emerald-400" />} title="Add repositories" desc="Paste a clone URL; every branch is indexed in the background." />
                <Point icon={<RotateCw className="size-4 text-emerald-400" />} title="Re-index" desc="Retry a failed branch, or rebuild a whole project after it changes." />
                <Point icon={<Activity className="size-4 text-emerald-400" />} title="Health checks" desc="Spot branches whose search index went missing, and leftovers from deletions." />
                <Point icon={<Users className="size-4 text-emerald-400" />} title="Manage users" desc="Promote trusted users to administrator, or remove access." />
              </CardContent>
            </Card>
          </div>

          <div className="mt-10 flex justify-center">
            <Button asChild size="lg">
              <Link href="/register">Create a free account</Link>
            </Button>
          </div>
        </div>
      </section>
    </main>
  )
}

function Step(props: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="inline-flex size-9 items-center justify-center rounded-md bg-emerald-50 dark:bg-emerald-950">{props.icon}</div>
        <CardTitle className="text-base">{props.title}</CardTitle>
        <CardDescription>{props.desc}</CardDescription>
      </CardHeader>
    </Card>
  )
}

function Point(props: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5">{props.icon}</div>
      <div>
        <div className="font-medium">{props.title}</div>
        <div className="text-muted-foreground">{props.desc}</div>
      </div>
    </div>
  )
}
