"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useSWRConfig } from "swr"
import { toast } from "sonner"
import { AlertCircle, Check, Circle, Loader2 } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError, errorMessage } from "@/lib/api/client"
import { keys, login, register } from "@/lib/api/endpoints"
import { LIMITS } from "@/lib/format"
import { cn } from "@/lib/utils"

// Mirrors UserCreate in server/app/schemas/user.py.
const PASSWORD_RULES = [
  { label: `At least ${LIMITS.passwordMin} characters`, test: (p: string) => p.length >= LIMITS.passwordMin },
  { label: "Contains a letter", test: (p: string) => /[A-Za-z]/.test(p) },
  { label: "Contains a number", test: (p: string) => /\d/.test(p) },
]

type Field = "fullname" | "email" | "password" | "confirm"

export default function RegisterPage() {
  const router = useRouter()
  const { mutate } = useSWRConfig()
  const [values, setValues] = React.useState({ fullname: "", email: "", password: "", confirm: "" })
  const [fieldErrors, setFieldErrors] = React.useState<Partial<Record<Field, string>>>({})
  const [error, setError] = React.useState<string | null>(null)
  const [pending, setPending] = React.useState(false)

  const passwordOk = PASSWORD_RULES.every((r) => r.test(values.password))
  const confirmMismatch = values.confirm.length > 0 && values.confirm !== values.password
  const canSubmit =
    values.fullname.trim() && values.email.trim() && passwordOk && values.confirm === values.password

  function set(field: Field) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setValues((v) => ({ ...v, [field]: e.target.value }))
      setFieldErrors((fe) => ({ ...fe, [field]: undefined }))
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null)
    setFieldErrors({})
    setPending(true)

    const payload = {
      fullname: values.fullname.trim(),
      email: values.email.trim(),
      password: values.password,
    }

    try {
      await register(payload)
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
        setFieldErrors(err.fieldErrors as Partial<Record<Field, string>>)
      } else {
        setError(errorMessage(err))
      }
      setPending(false)
      return
    }

    // Account exists now; sign straight in so the user lands in the app.
    try {
      const user = await login({ email: payload.email, password: payload.password })
      await mutate(keys.me, user, { revalidate: false })
      toast.success("Account created", { description: `Welcome, ${user.fullname}.` })
      router.replace("/dashboard")
      router.refresh()
    } catch {
      toast.success("Account created", { description: "Please sign in to continue." })
      router.replace(`/login?email=${encodeURIComponent(payload.email)}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Create your account</h1>
        <p className="text-sm text-muted-foreground">
          Free to join. Upload your code and get targeted fixes in minutes.
        </p>
      </div>

      {error && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="size-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-4" onSubmit={onSubmit}>
        <FormField id="fullname" label="Full name" error={fieldErrors.fullname}>
          <Input
            id="fullname"
            autoComplete="name"
            placeholder="Ayesha Rahman"
            maxLength={100}
            value={values.fullname}
            onChange={set("fullname")}
            aria-invalid={Boolean(fieldErrors.fullname)}
            required
            autoFocus
          />
        </FormField>

        <FormField id="email" label="Email" error={fieldErrors.email}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={values.email}
            onChange={set("email")}
            aria-invalid={Boolean(fieldErrors.email)}
            required
          />
        </FormField>

        <FormField id="password" label="Password" error={fieldErrors.password}>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            maxLength={128}
            value={values.password}
            onChange={set("password")}
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby="password-rules"
            required
          />
          <ul id="password-rules" className="mt-2 space-y-1 text-xs">
            {PASSWORD_RULES.map((rule) => {
              const ok = rule.test(values.password)
              return (
                <li
                  key={rule.label}
                  className={cn("flex items-center gap-2", ok ? "text-emerald-700" : "text-muted-foreground")}
                >
                  {ok ? <Check className="size-3.5" /> : <Circle className="size-3.5" />}
                  {rule.label}
                </li>
              )
            })}
          </ul>
        </FormField>

        <FormField
          id="confirm"
          label="Confirm password"
          error={confirmMismatch ? "Passwords do not match" : undefined}
        >
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            value={values.confirm}
            onChange={set("confirm")}
            aria-invalid={confirmMismatch}
            required
          />
        </FormField>

        <Button
          type="submit"
          className="w-full bg-emerald-600 hover:bg-emerald-700"
          disabled={pending || !canSubmit}
        >
          {pending && <Loader2 className="animate-spin" />}
          {pending ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-foreground underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </div>
  )
}

function FormField(props: { id: string; label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label htmlFor={props.id}>{props.label}</Label>
      {props.children}
      {props.error && (
        <p className="text-xs font-medium text-destructive" role="alert">
          {props.error}
        </p>
      )}
    </div>
  )
}
