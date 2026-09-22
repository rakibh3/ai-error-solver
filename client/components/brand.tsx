import Link from "next/link"
import { cn } from "@/lib/utils"

export const APP_NAME = "Linefix"

// Three lines of code with a prompt marker pointing at the middle one:
// the exact line Linefix tells you to change. Kept in sync with app/icon.svg.
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={cn("size-7 shrink-0", className)}
    >
      <rect width="32" height="32" rx="8" fill="#10b981" />
      <g stroke="#022c22" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 9.5h13" strokeWidth="2.6" strokeOpacity=".35" />
        <path d="M7.5 13.5 10 16l-2.5 2.5" strokeWidth="2.2" />
        <path d="M13.5 16h10" strokeWidth="2.6" />
        <path d="M10 22.5h8" strokeWidth="2.6" strokeOpacity=".35" />
      </g>
    </svg>
  )
}

export function Brand({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link
      href={href}
      aria-label={`${APP_NAME} home`}
      className={cn("flex items-center gap-2.5 text-lg font-bold tracking-tight", className)}
    >
      <BrandMark />
      <span>
        Line<span className="text-emerald-400">fix</span>
      </span>
    </Link>
  )
}
