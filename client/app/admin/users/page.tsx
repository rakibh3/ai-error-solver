"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { toast } from "sonner"
import { ChevronLeft, ChevronRight, Search, ShieldCheck, UserRound, Users } from "lucide-react"
import { ConfirmDialog, EmptyState, ErrorState, PageHeader } from "@/components/app/common"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useSession } from "@/hooks/use-session"
import { errorMessage } from "@/lib/api/client"
import { keys, listUsers, updateUserRole } from "@/lib/api/endpoints"
import type { User, UserRole } from "@/lib/api/types"
import { initials } from "@/lib/format"

const PAGE_SIZE = 25

export default function UsersPage() {
  const router = useRouter()
  const { mutate: globalMutate } = useSWRConfig()
  const { user: me } = useSession()
  const [page, setPage] = React.useState(0)
  const [query, setQuery] = React.useState("")
  const [pendingChange, setPendingChange] = React.useState<{ user: User; role: UserRole } | null>(null)

  const offset = page * PAGE_SIZE
  const users = useSWR(keys.users(PAGE_SIZE, offset), () => listUsers(PAGE_SIZE, offset), {
    keepPreviousData: true,
  })

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return users.data ?? []
    return (users.data ?? []).filter(
      (u) => u.fullname.toLowerCase().includes(q) || u.email.toLowerCase().includes(q) || String(u.id) === q,
    )
  }, [users.data, query])

  const hasNext = (users.data?.length ?? 0) === PAGE_SIZE

  async function applyRoleChange() {
    if (!pendingChange) return
    const { user, role } = pendingChange
    try {
      const updated = await updateUserRole(user.id, role)
      toast.success("Role updated", {
        description: `${updated.fullname} is now ${updated.role === "ADMIN" ? "an administrator" : "a regular user"}.`,
      })
      await users.mutate((list) => list?.map((u) => (u.id === updated.id ? updated : u)), { revalidate: false })
      if (updated.id === me?.id) {
        // You just removed your own admin access.
        await globalMutate(keys.me, updated, { revalidate: false })
        router.replace("/dashboard")
      }
    } catch (err) {
      toast.error("Could not change role", { description: errorMessage(err) })
      throw err
    }
  }

  const promoting = pendingChange?.role === "ADMIN"
  const demotingSelf = pendingChange && !promoting && pendingChange.user.id === me?.id

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Every registered account. Promoting a user to administrator is the only way to grant admin access."
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter this page by name or email"
            className="pl-8"
            aria-label="Filter users"
          />
        </div>
        <Pager page={page} hasNext={hasNext} onPage={setPage} loading={users.isValidating} />
      </div>

      {users.error ? (
        <ErrorState error={users.error} onRetry={() => users.mutate()} />
      ) : !users.data ? (
        <Skeleton className="h-80 w-full rounded-xl" />
      ) : users.data.length === 0 ? (
        <EmptyState icon={<Users className="size-6" />} title="No users on this page" />
      ) : (
        <Card className="overflow-hidden py-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="pl-4">User</TableHead>
                <TableHead className="hidden sm:table-cell">ID</TableHead>
                <TableHead className="hidden md:table-cell">Status</TableHead>
                <TableHead className="w-44 pr-4">Role</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="pl-4">
                    <div className="flex items-center gap-3">
                      <Avatar className="size-8">
                        <AvatarFallback className="bg-muted text-xs">{initials(u.fullname)}</AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-medium">{u.fullname}</span>
                          {u.id === me?.id && <Badge variant="secondary">You</Badge>}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">{u.email}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="hidden font-mono text-xs text-muted-foreground sm:table-cell">#{u.id}</TableCell>
                  <TableCell className="hidden md:table-cell">
                    {u.is_active ? (
                      <Badge variant="outline" className="border-emerald-200 text-emerald-800 dark:border-emerald-900 dark:text-emerald-300">Active</Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground">Deactivated</Badge>
                    )}
                  </TableCell>
                  <TableCell className="pr-4">
                    <Select
                      value={u.role}
                      onValueChange={(role) => role !== u.role && setPendingChange({ user: u, role: role as UserRole })}
                    >
                      <SelectTrigger className="h-8 w-full" aria-label={`Role for ${u.fullname}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USER">
                          <UserRound />
                          User
                        </SelectItem>
                        <SelectItem value="ADMIN">
                          <ShieldCheck />
                          Administrator
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">
                    No users on this page match “{query}”.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(pendingChange)}
        onOpenChange={(o) => !o && setPendingChange(null)}
        title={promoting ? "Grant administrator access?" : "Remove administrator access?"}
        description={
          promoting ? (
            <p>
              <strong className="text-foreground">{pendingChange?.user.fullname}</strong> will be able to manage
              reference projects, see every user&apos;s submissions, and change anyone&apos;s role — including yours.
            </p>
          ) : (
            <>
              <p>
                <strong className="text-foreground">{pendingChange?.user.fullname}</strong> will become a regular
                user and lose access to the admin area.
              </p>
              {demotingSelf && (
                <p className="font-medium text-destructive">
                  This is your own account. You will lose admin access immediately.
                </p>
              )}
              <p>The last remaining administrator cannot be demoted.</p>
            </>
          )
        }
        confirmLabel={promoting ? "Make administrator" : "Remove admin access"}
        destructive={!promoting}
        onConfirm={applyRoleChange}
      />
    </div>
  )
}

function Pager(props: { page: number; hasNext: boolean; onPage: (p: number) => void; loading: boolean }) {
  return (
    <div className="flex items-center gap-2 self-end sm:self-auto">
      <span className="text-sm text-muted-foreground">Page {props.page + 1}</span>
      <Button
        size="icon"
        variant="outline"
        className="size-8"
        onClick={() => props.onPage(props.page - 1)}
        disabled={props.page === 0 || props.loading}
        aria-label="Previous page"
      >
        <ChevronLeft />
      </Button>
      <Button
        size="icon"
        variant="outline"
        className="size-8"
        onClick={() => props.onPage(props.page + 1)}
        disabled={!props.hasNext || props.loading}
        aria-label="Next page"
      >
        <ChevronRight />
      </Button>
    </div>
  )
}
