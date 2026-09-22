import Link from "next/link"
import { cookies } from "next/headers"
import { ArrowRight } from "lucide-react"
import { Brand } from "@/components/brand"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { SESSION_COOKIE } from "@/lib/server/session"

// Marketing header. Only checks whether a session cookie exists to pick the
// call to action; the token itself is validated by the API, not here.
export async function SiteHeader({ className }: { className?: string }) {
  const signedIn = Boolean((await cookies()).get(SESSION_COOKIE)?.value)

  return (
    <header className={cn("sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur", className)}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Brand />
        <nav className="hidden gap-6 text-sm md:flex" aria-label="Main">
          <Link href="/how-it-works" className="text-muted-foreground hover:text-foreground">
            How it works
          </Link>
          <Link href="/faq" className="text-muted-foreground hover:text-foreground">
            FAQ
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          {signedIn ? (
            <Button asChild size="sm">
              <Link href="/dashboard">
                Open dashboard
                <ArrowRight />
              </Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">Sign in</Link>
              </Button>
              <Button asChild size="sm">
                <Link href="/register">
                  Get started
                  <ArrowRight />
                </Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
