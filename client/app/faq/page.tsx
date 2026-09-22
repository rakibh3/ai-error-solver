import Link from "next/link"
import * as AccordionPrimitive from "@radix-ui/react-accordion"
import { ArrowRight, Plus } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { Accordion, AccordionContent, AccordionItem } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const FAQS: { id: string; q: string; a: React.ReactNode }[] = [
  {
    id: "how-start",
    q: "How do I get a fix for my error?",
    a: (
      <ol className="list-inside list-decimal space-y-1">
        <li>Create an account and sign in.</li>
        <li>Upload your project folder (or a .zip) from your dashboard.</li>
        <li>Pick the reference project and branch your code should match.</li>
        <li>Paste the full error or traceback and click “Find the fix”.</li>
      </ol>
    ),
  },
  {
    id: "traceback",
    q: "Why should I paste the whole traceback?",
    a: "The file paths in the traceback decide which of your files are sent for analysis. With only the last line, the relevant file may be missed and the answer will be less precise.",
  },
  {
    id: "limits",
    q: "What are the upload limits?",
    a: (
      <ul className="list-inside list-disc space-y-1">
        <li>25 MB per upload (compressed), 50 MB once extracted</li>
        <li>Up to 2,000 files, each under 10 MB</li>
        <li>5 submissions and 200 MB of storage per account — delete one to free up space</li>
      </ul>
    ),
  },
  {
    id: "ignored",
    q: "Does it upload node_modules or my virtualenv?",
    a: "No. Folders like node_modules, .venv, .next, dist, build and .git, and lockfiles, are skipped in your browser before uploading, and stripped again on the server. They never count toward your quota.",
  },
  {
    id: "failed",
    q: "What does it mean when an analysis “failed”?",
    a: "The model could not produce a usable fix for that attempt. It is still saved in your history with the reason. Try again with the full traceback, or compare against a different branch.",
  },
  {
    id: "rate",
    q: "Why was I told to wait before trying again?",
    a: "Analyses and uploads are rate-limited per account to keep the service responsive for everyone. Wait a little while and try again.",
  },
  {
    id: "no-references",
    q: "I can't find a reference to compare against.",
    a: "References are added by administrators, and a branch only appears once it has finished indexing. If the one you need is missing, ask an administrator to add it.",
  },
  {
    id: "privacy",
    q: "Who can see my uploads?",
    a: "Only you and administrators. Deleting a submission permanently removes its files and its entire analysis history.",
  },
  {
    id: "admin",
    q: "How do I become an administrator?",
    a: "Every new account is a regular user. An existing administrator can promote you from the Users page.",
  },
]

const GROUPS: { title: string; ids: string[] }[] = [
  { title: "Getting a fix", ids: ["how-start", "traceback", "failed", "rate"] },
  { title: "Uploads & references", ids: ["limits", "ignored", "no-references"] },
  { title: "Accounts & privacy", ids: ["privacy", "admin"] },
]

export default function FAQPage() {
  let n = 0
  return (
    <main>
      <SiteHeader />
      <section className="relative isolate overflow-hidden py-12 md:py-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-72 bg-[radial-gradient(50%_100%_at_50%_0%,rgb(16_185_129/0.12),transparent)]"
        />
        <div className="container mx-auto max-w-3xl px-4">
          <header className="mb-10 space-y-3">
            <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-300 dark:hover:bg-emerald-500/15">
              FAQ
            </Badge>
            <h1 className="text-balance text-3xl font-bold tracking-tight md:text-4xl">Common questions</h1>
            <p className="text-pretty text-muted-foreground">
              Uploads, references, limits and privacy — what people ask before and after their first fix.
            </p>
          </header>

          <Accordion type="single" collapsible defaultValue="how-start" className="space-y-10">
            {GROUPS.map((group) => (
              <div key={group.title} className="space-y-3">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{group.title}</h2>
                {group.ids.map((id) => {
                  const f = FAQS.find((x) => x.id === id)!
                  n += 1
                  return <FaqItem key={id} index={n} faq={f} />
                })}
              </div>
            ))}
          </Accordion>

          <div className="mt-12 flex flex-col items-start justify-between gap-4 rounded-xl border bg-card p-6 sm:flex-row sm:items-center">
            <div>
              <p className="font-semibold">Still stuck?</p>
              <p className="text-sm text-muted-foreground">See the full walkthrough, or upload your project and try it.</p>
            </div>
            <div className="flex gap-3">
              <Button asChild variant="outline">
                <Link href="/how-it-works">How it works</Link>
              </Button>
              <Button asChild>
                <Link href="/register">
                  Get started
                  <ArrowRight />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function FaqItem({ index, faq }: { index: number; faq: (typeof FAQS)[number] }) {
  return (
    <AccordionItem
      value={faq.id}
      className="group/item rounded-xl border bg-card/40 transition-[border-color,background-color] duration-200 last:border-b hover:border-emerald-500/30 data-[state=open]:border-emerald-500/40 data-[state=open]:bg-card"
    >
      <AccordionPrimitive.Header className="flex">
        <AccordionPrimitive.Trigger className="flex flex-1 items-center gap-4 rounded-xl px-5 py-4 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50">
          <span className="w-6 shrink-0 font-mono text-sm tabular-nums text-muted-foreground transition-colors group-data-[state=open]/item:text-emerald-400">
            {String(index).padStart(2, "0")}
          </span>
          <span className="flex-1 text-pretty font-medium">{faq.q}</span>
          <span className="grid size-8 shrink-0 place-items-center rounded-full border transition-[background-color,border-color,color] duration-200 group-hover/item:border-emerald-500/40 group-data-[state=open]/item:border-transparent group-data-[state=open]/item:bg-primary group-data-[state=open]/item:text-primary-foreground">
            <Plus className="size-4 transition-transform duration-200 group-data-[state=open]/item:rotate-45" />
          </span>
        </AccordionPrimitive.Trigger>
      </AccordionPrimitive.Header>
      <AccordionContent className="pb-5 pl-15 pr-5 sm:pr-14 leading-relaxed text-pretty text-muted-foreground">{faq.a}</AccordionContent>
    </AccordionItem>
  )
}
