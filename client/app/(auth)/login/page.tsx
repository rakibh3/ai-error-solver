"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useSWRConfig } from "swr"
import { AlertCircle, Loader2 } from "lucide-react"
import { PasswordInput } from "@/components/auth/password-input"
import { APP_NAME } from "@/components/brand"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { ApiError, errorMessage } from "@/lib/api/client"
import { keys, login } from "@/lib/api/endpoints"
import { type LoginValues, loginSchema } from "@/lib/validation/auth"

/**
 * Only allow same-site relative paths, so `?next=` cannot be an open redirect.
 * Parse with URL rather than prefix checks: URL strips tabs/newlines, so
 * "/\t/evil.com" would otherwise pass a string check and resolve off-site.
 */
function safeNext(next: string | null): string {
  if (!next) return "/dashboard"
  try {
    const base = "http://same.invalid"
    const url = new URL(next, base)
    if (url.origin !== base) return "/dashboard"
    return `${url.pathname}${url.search}${url.hash}`
  } catch {
    return "/dashboard"
  }
}

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const { mutate } = useSWRConfig()
  const [error, setError] = React.useState<string | null>(null)
  const [redirecting, setRedirecting] = React.useState(false)
  const prefilledEmail = params.get("email") ?? ""

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    mode: "onTouched",
    defaultValues: { email: prefilledEmail, password: "" },
  })
  const pending = form.formState.isSubmitting || redirecting

  // Coming from registration the email is known, so start on the password.
  React.useEffect(() => {
    form.setFocus(prefilledEmail ? "password" : "email")
  }, [form, prefilledEmail])

  async function onSubmit(values: LoginValues) {
    setError(null)
    try {
      const user = await login(values)
      setRedirecting(true)
      await mutate(keys.me, user, { revalidate: false })
      router.replace(safeNext(params.get("next")))
      router.refresh()
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.fieldErrors).length) {
        for (const [field, message] of Object.entries(err.fieldErrors)) {
          if (field === "email" || field === "password") form.setError(field, { message })
        }
        return
      }
      setError(errorMessage(err))
      form.resetField("password")
      form.setFocus("password")
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
        <p className="text-sm text-muted-foreground">Sign in to {APP_NAME} to pick up where you left off.</p>
      </div>

      {error && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="size-4" />
          <AlertTitle>Couldn&apos;t sign you in</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Form {...form}>
        <form className="space-y-5" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="email" inputMode="email" placeholder="you@example.com" {...field} />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <PasswordInput autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
          <Button type="submit" size="lg" className="w-full font-semibold" disabled={pending}>
            {pending && <Loader2 className="animate-spin" />}
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Form>

      <p className="text-center text-sm text-muted-foreground">
        New to {APP_NAME}?{" "}
        <Link href="/register" className="font-medium text-emerald-400 underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  )
}

export default function LoginPage() {
  return (
    <React.Suspense>
      <LoginForm />
    </React.Suspense>
  )
}
