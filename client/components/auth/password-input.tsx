"use client"

import * as React from "react"
import { ArrowBigUp, Eye, EyeOff } from "lucide-react"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

/**
 * Password field with a show/hide toggle and a Caps Lock hint. Spreads all
 * props (including ref, id and aria-* from FormControl) onto the <input>.
 */
export function PasswordInput({ className, onKeyDown, onKeyUp, onBlur, ...props }: React.ComponentProps<"input">) {
  const [visible, setVisible] = React.useState(false)
  const [capsLock, setCapsLock] = React.useState(false)

  const trackCaps = (e: React.KeyboardEvent<HTMLInputElement>) => setCapsLock(e.getModifierState("CapsLock"))

  return (
    <div className="space-y-1.5">
      <div className="relative">
        <Input
          {...props}
          type={visible ? "text" : "password"}
          className={cn("pr-10", className)}
          onKeyDown={(e) => {
            trackCaps(e)
            onKeyDown?.(e)
          }}
          onKeyUp={(e) => {
            trackCaps(e)
            onKeyUp?.(e)
          }}
          onBlur={(e) => {
            setCapsLock(false)
            onBlur?.(e)
          }}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          className="absolute inset-y-0 right-0 grid w-10 place-items-center rounded-r-md text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          {visible ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
        </button>
      </div>
      {capsLock && (
        <p className="flex items-center gap-1.5 text-xs text-amber-300" role="status">
          <ArrowBigUp className="size-3.5" aria-hidden="true" />
          Caps Lock is on
        </p>
      )}
    </div>
  )
}
