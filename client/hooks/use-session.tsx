"use client"

import * as React from "react"
import { usePathname, useRouter } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { toast } from "sonner"
import { SESSION_EXPIRED_EVENT } from "@/lib/api/client"
import { getMe, keys, logout } from "@/lib/api/endpoints"
import type { User } from "@/lib/api/types"

interface SessionValue {
  user: User | undefined
  isLoading: boolean
  isAdmin: boolean
  signOut: () => Promise<void>
}

const SessionContext = React.createContext<SessionValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { mutate } = useSWRConfig()
  const { data: user, isLoading } = useSWR(keys.me, getMe, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  })

  const clearCache = React.useCallback(
    () => mutate(() => true, undefined, { revalidate: false }),
    [mutate],
  )

  React.useEffect(() => {
    let handled = false
    function onExpired() {
      if (handled) return
      handled = true
      toast.error("Session expired", { description: "Please sign in again." })
      void logout().then(clearCache)
      router.replace(`/login?next=${encodeURIComponent(pathname)}`)
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [router, pathname, clearCache])

  const signOut = React.useCallback(async () => {
    await logout()
    await clearCache()
    router.replace("/login")
    router.refresh()
  }, [router, clearCache])

  const value = React.useMemo<SessionValue>(
    () => ({ user, isLoading, isAdmin: user?.role === "ADMIN", signOut }),
    [user, isLoading, signOut],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionValue {
  const ctx = React.useContext(SessionContext)
  if (!ctx) throw new Error("useSession must be used inside <SessionProvider>")
  return ctx
}
