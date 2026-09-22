"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useSWRConfig } from "swr"
import { toast } from "sonner"
import { AlertCircle, Check, Circle, Loader2, X } from "lucide-react"
import { PasswordInput } from "@/components/auth/password-input"
import { APP_NAME } from "@/components/brand"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage, useFormField } from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { ApiError, errorMessage } from "@/lib/api/client"
import { keys, login, register } from "@/lib/api/endpoints"
import { cn } from "@/lib/utils"
import { PASSWORD_RULES, type RegisterValues, registerSchema } from "@/lib/validation/auth"

const FIELDS = ["fullname", "email", "password", "confirm"] as const

export default function RegisterPage() {
  const router = useRouter()
  const { mutate } = useSWRConfig()
  const [error, setError] = React.useState<string | null>(null)
  const [redirecting, setRedirecting] = React.useState(false)

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    mode: "onTouched",
    defaultValues: { fullname: "", email: "", password: "", confirm: "" },
  })
  const pending = form.formState.isSubmitting || redirecting
  const password = form.watch("password")
  const passwordTouched = form.formState.touchedFields.password || form.formState.isSubmitted

  React.useEffect(() => {
    form.setFocus("fullname")
  }, [form])

  async function onSubmit(values: RegisterValues) {
    setError(null)
    const payload = { fullname: values.fullname, email: values.email, password: values.password }

    try {
      await register(payload)
    } catch (err) {
      const fieldErrors = err instanceof ApiError ? Object.entries(err.fieldErrors) : []
      const known = fieldErrors.filter(([f]) => (FIELDS as readonly string[]).includes(f))
      if (known.length) {
        known.forEach(([field, message], i) =>
          form.setError(field as (typeof FIELDS)[number], { message }, { shouldFocus: i === 0 }),
        )
      } else {
        setError(errorMessage(err))
      }
      return
    }

    // Account exists now; sign straight in so the user lands in the app.
    setRedirecting(true)
    try {
      const user = await login({ email: payload.email, password: payload.password })
      await mutate(keys.me, user, { revalidate: false })
      toast.success("Account created", { description: `Welcome to ${APP_NAME}, ${user.fullname}.` })
      router.replace("/dashboard")
      router.refresh()
    } catch {
      toast.success("Account created", { description: "Please sign in to continue." })
      router.replace(`/login?email=${encodeURIComponent(payload.email)}`)
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Create your account</h1>
        <p className="text-sm text-muted-foreground">Free to join. Upload your code and get a targeted fix in minutes.</p>
      </div>

      {error && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="size-4" />
          <AlertTitle>Couldn&apos;t create your account</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Form {...form}>
        <form className="space-y-5" onSubmit={form.handleSubmit(onSubmit)} noValidate>
          <FormField
            control={form.control}
            name="fullname"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Full name</FormLabel>
                <FormControl>
                  <Input autoComplete="name" placeholder="Ayesha Rahman" maxLength={100} {...field} />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
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
                  <PasswordInput autoComplete="new-password" maxLength={128} {...field} />
                </FormControl>
                <FormMessage role="alert" />
                <PasswordRules password={password} touched={Boolean(passwordTouched)} />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirm"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirm password</FormLabel>
                <FormControl>
                  <PasswordInput autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage role="alert" />
              </FormItem>
            )}
          />
          <Button type="submit" size="lg" className="w-full font-semibold" disabled={pending}>
            {pending && <Loader2 className="animate-spin" />}
            {pending ? "Creating account…" : "Create account"}
          </Button>
        </form>
      </Form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-emerald-400 underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  )
}


// Rendered as the field's description so FormControl's aria-describedby
// already points the password input at these requirements.
function PasswordRules({ password, touched }: { password: string; touched: boolean }) {
  const { formDescriptionId } = useFormField()
  return (
    <ul id={formDescriptionId} className="flex flex-wrap gap-x-4 gap-y-1.5 pt-1 text-xs" aria-label="Password requirements">
      {PASSWORD_RULES.map((rule) => {
        const ok = rule.test(password)
        const failed = !ok && touched
        return (
          <li
            key={rule.label}
            className={cn(
              "flex items-center gap-1.5 transition-colors",
              ok ? "text-emerald-400" : failed ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {ok ? (
              <Check className="size-3.5 shrink-0" aria-hidden="true" />
            ) : failed ? (
              <X className="size-3.5 shrink-0" aria-hidden="true" />
            ) : (
              <Circle className="size-3.5 shrink-0" aria-hidden="true" />
            )}
            <span>
              {rule.label}
              <span className="sr-only">{ok ? " — met" : " — not met"}</span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}
