"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { SWRConfig } from "swr"
import {
  Activity,
  FolderGit2,
  FolderUp,
  LogOut,
  Menu,
  ShieldCheck,
  Users,
} from "lucide-react"
import { Brand } from "@/components/brand"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { TooltipProvider } from "@/components/ui/tooltip"
import { SessionProvider, useSession } from "@/hooks/use-session"
import { initials } from "@/lib/format"
import { cn } from "@/lib/utils"

type NavItem = { href: string; label: string; icon: React.ReactNode; adminOnly?: boolean }

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Submissions", icon: <FolderUp className="size-4" /> },
  { href: "/admin/references", label: "References", icon: <FolderGit2 className="size-4" />, adminOnly: true },
  { href: "/admin/users", label: "Users", icon: <Users className="size-4" />, adminOnly: true },
  { href: "/admin/health", label: "System health", icon: <Activity className="size-4" />, adminOnly: true },
]

function isActive(pathname: string, href: string) {
  return href === "/dashboard"
    ? pathname === "/dashboard" || pathname.startsWith("/dashboard/")
    : pathname.startsWith(href)
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ revalidateOnFocus: true, shouldRetryOnError: false }}>
      <SessionProvider>
        <TooltipProvider delayDuration={200}>
          <div className="min-h-dvh bg-muted/30">
            <TopBar />
            <main className="container mx-auto max-w-6xl px-4 py-8">{children}</main>
          </div>
        </TooltipProvider>
      </SessionProvider>
    </SWRConfig>
  )
}

/**
 * UX gate for admin pages. The API enforces the role on every admin endpoint
 * (403); this only avoids rendering screens that would fail.
 */
export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAdmin } = useSession()

  if (isLoading || !user) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <div className="mx-auto mb-4 inline-flex size-12 items-center justify-center rounded-full bg-muted">
          <ShieldCheck className="size-6 text-muted-foreground" />
        </div>
        <h1 className="text-xl font-semibold">Administrator access required</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This area is only available to administrators. If you need access, ask an existing admin to
          change your role.
        </p>
        <Button asChild className="mt-6" variant="outline">
          <Link href="/dashboard">Back to your submissions</Link>
        </Button>
      </div>
    )
  }
  return <>{children}</>
}

function TopBar() {
  const pathname = usePathname()
  const { isAdmin } = useSession()
  const items = NAV.filter((i) => !i.adminOnly || isAdmin)
  const [open, setOpen] = React.useState(false)

  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="container mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
              <Menu />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72">
            <SheetHeader>
              <SheetTitle>
                <Brand href="/dashboard" />
              </SheetTitle>
            </SheetHeader>
            <nav className="grid gap-1 px-4" aria-label="App">
              {items.map((item) => (
                <NavLink key={item.href} item={item} active={isActive(pathname, item.href)} onClick={() => setOpen(false)} />
              ))}
            </nav>
          </SheetContent>
        </Sheet>

        <Brand href="/dashboard" className="hidden sm:flex" />

        <nav className="hidden items-center gap-1 md:flex" aria-label="App">
          {items.map((item) => (
            <NavLink key={item.href} item={item} active={isActive(pathname, item.href)} />
          ))}
        </nav>

        <div className="ml-auto">
          <UserMenu />
        </div>
      </div>
    </header>
  )
}

function NavLink({ item, active, onClick }: { item: NavItem; active: boolean; onClick?: () => void }) {
  return (
    <Link
      href={item.href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
          : "text-muted-foreground hover:bg-accent hover:text-foreground",
      )}
    >
      {item.icon}
      {item.label}
    </Link>
  )
}

function UserMenu() {
  const { user, isLoading, isAdmin, signOut } = useSession()

  if (isLoading || !user) return <Skeleton className="size-8 rounded-full" />

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-9 gap-2 px-2" aria-label="Account menu">
          <Avatar className="size-7">
            <AvatarFallback className="bg-emerald-100 text-xs font-semibold text-emerald-800">
              {initials(user.fullname)}
            </AvatarFallback>
          </Avatar>
          <span className="hidden max-w-40 truncate text-sm font-medium sm:inline">{user.fullname}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="space-y-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate">{user.fullname}</span>
            {isAdmin && (
              <Badge variant="outline" className="gap-1 border-emerald-200 text-emerald-800">
                <ShieldCheck className="size-3" />
                Admin
              </Badge>
            )}
          </div>
          <div className="truncate text-xs font-normal text-muted-foreground">{user.email}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/">Home page</Link>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void signOut()}>
          <LogOut />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
