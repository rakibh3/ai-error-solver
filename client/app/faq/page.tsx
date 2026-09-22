import { SiteHeader } from "@/components/site-header"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Badge } from "@/components/ui/badge"

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

export default function FAQPage() {
  return (
    <main>
      <SiteHeader />
      <section className="py-12 md:py-16">
        <div className="container mx-auto max-w-3xl px-4">
          <div className="mb-6 flex items-center gap-2">
            <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">FAQ</Badge>
            <span className="text-muted-foreground">Common questions</span>
          </div>

          <Accordion type="single" collapsible className="w-full">
            {FAQS.map((f) => (
              <AccordionItem key={f.id} value={f.id}>
                <AccordionTrigger>{f.q}</AccordionTrigger>
                <AccordionContent className="text-muted-foreground">{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>
    </main>
  )
}
