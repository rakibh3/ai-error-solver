import Link from "next/link"
import { cn } from "@/lib/utils"

export const APP_NAME = "AI Error Solver"

export function BrandMark({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn("size-6 rounded-md bg-gradient-to-tr from-emerald-500 to-emerald-700", className)}
    />
  )
}

export function Brand({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={cn("flex items-center gap-2 font-semibold", className)}>
      <BrandMark />
      <span>{APP_NAME}</span>
    </Link>
  )
}
