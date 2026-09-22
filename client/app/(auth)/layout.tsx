import { CheckCircle2 } from "lucide-react"
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
        <Brand />
        <main className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">{children}</div>
        </main>
      </div>
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-emerald-600 via-emerald-700 to-emerald-900 text-white lg:flex lg:flex-col lg:justify-center lg:px-16">
        <div className="absolute -right-24 -top-24 size-96 rounded-full bg-emerald-400/30 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 size-96 rounded-full bg-emerald-300/20 blur-3xl" />
        <div className="relative max-w-md space-y-6">
          <h2 className="text-3xl font-semibold leading-tight">
            Stop guessing. See exactly what differs from a working solution.
          </h2>
          <ul className="space-y-3 text-emerald-50">
            {POINTS.map((p) => (
              <li key={p} className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-200" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  )
}
