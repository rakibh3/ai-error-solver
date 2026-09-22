import Link from "next/link"
import { ArrowLeft, CheckCircle2 } from "lucide-react"
import { Brand } from "@/components/brand"

const POINTS = [
  "Upload your project as a folder or a .zip",
  "Compare it against a curated reference solution",
  "Get the exact file, line, and replacement to fix it",
]

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-10">
        <div className="flex items-center justify-between">
          <Brand />
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to home
          </Link>
        </div>
        <main className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">{children}</div>
        </main>
      </div>

      <aside className="relative isolate hidden overflow-hidden border-l bg-card lg:flex lg:flex-col lg:justify-center lg:px-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(to_right,rgb(255_255_255/0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgb(255_255_255/0.04)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]"
        />
        <div aria-hidden="true" className="absolute -right-24 -top-24 -z-10 size-96 rounded-full bg-emerald-500/20 blur-3xl" />
        <div aria-hidden="true" className="absolute -bottom-24 -left-24 -z-10 size-96 rounded-full bg-teal-500/10 blur-3xl" />

        <div className="max-w-md space-y-8">
          <div className="space-y-6">
            <h2 className="text-balance text-3xl font-bold leading-tight tracking-tight">
              Stop guessing. See exactly what differs from a working solution.
            </h2>
            <ul className="space-y-3 text-muted-foreground">
              {POINTS.map((p) => (
                <li key={p} className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-400" aria-hidden="true" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>

          <figure
            aria-label="Example fix"
            className="overflow-hidden rounded-xl border bg-background/80 font-mono text-sm shadow-2xl shadow-emerald-950/40 backdrop-blur"
          >
            <figcaption className="flex justify-between border-b px-4 py-2.5 text-xs text-muted-foreground">
              <span>app/routes/items.py</span>
              <span>line 24</span>
            </figcaption>
            <div className="bg-red-500/10 px-4 py-2 text-red-300">- return item.serialise()</div>
            <div className="bg-emerald-500/10 px-4 py-2 text-emerald-300">+ return item.serialize()</div>
          </figure>
        </div>
      </aside>
    </div>
  )
}
