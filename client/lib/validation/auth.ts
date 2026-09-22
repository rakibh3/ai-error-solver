import { z } from "zod"
import { LIMITS } from "@/lib/format"

// Mirrors UserCreate / UserLogin in server/app/schemas/user.py so users see the
// same rules before submitting that the API enforces after.

const email = z
  .string()
  .trim()
  .min(1, "Enter your email address")
  .email("Enter a valid email address, like you@example.com")

export const PASSWORD_RULES = [
  { label: `At least ${LIMITS.passwordMin} characters`, test: (p: string) => p.length >= LIMITS.passwordMin },
  { label: "Contains a letter", test: (p: string) => /[A-Za-z]/.test(p) },
  { label: "Contains a number", test: (p: string) => /\d/.test(p) },
]

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Enter your password"),
})

export const registerSchema = z
  .object({
    fullname: z.string().trim().min(1, "Enter your full name").max(100, "Keep your name under 100 characters"),
    email,
    password: z
      .string()
      .min(1, "Create a password")
      .max(128, "Keep your password under 128 characters")
      .refine((p) => PASSWORD_RULES.every((r) => r.test(p)), "Password doesn't meet all the requirements below"),
    confirm: z.string().min(1, "Re-enter your password"),
  })
  .refine((v) => v.confirm === v.password, { path: ["confirm"], message: "Passwords don't match" })

export type LoginValues = z.infer<typeof loginSchema>
export type RegisterValues = z.infer<typeof registerSchema>
