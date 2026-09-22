import { NextResponse } from "next/server"
import { SESSION_COOKIE, isSameOrigin } from "@/lib/server/session"

export async function POST(request: Request) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request rejected" }, { status: 403 })
  }
  const response = NextResponse.json({ status: "success" })
  response.cookies.delete(SESSION_COOKIE)
  return response
}
