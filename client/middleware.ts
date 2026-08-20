import { type NextRequest } from "next/server";
import { updateSession } from "./lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: [
    // Excludes /api/* entirely (auth is checked per-route inside API
    // handlers instead). Note: (?!api(?:/|$)) not just (?!api) — the bare
    // version would also wrongly exclude something like /apiary, since
    // it's a substring match, not a path-segment match.
    "/((?!api(?:/|$)|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};