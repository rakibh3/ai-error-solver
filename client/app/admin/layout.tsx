import { AdminGuard, AppShell } from "@/components/app/app-shell"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <AdminGuard>{children}</AdminGuard>
    </AppShell>
  )
}
