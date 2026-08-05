import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_ROUTES = ["/", "/sign-in", "/sign-up", "/auth/callback"];

function isPublicRoute(pathname: string): boolean {
    return PUBLIC_ROUTES.some((route) =>
        route === "/" ? pathname === "/" : pathname === route || pathname.startsWith(`${route}/`)
    );
}

export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({ request });

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll();
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value }) =>
                        request.cookies.set(name, value)
                    );
                    response = NextResponse.next({ request });
                    cookiesToSet.forEach(({ name, value, options }) =>
                        response.cookies.set(name, value, options)
                    );
                },
            },
        }
    );

    const {
        data: { user },
    } = await supabase.auth.getUser();

    const { pathname } = request.nextUrl;

    // Redirect logged-in users away from /sign-in or /sign-up
    if (user && (pathname === "/sign-in" || pathname === "/sign-up")) {
        const homeUrl = request.nextUrl.clone();
        homeUrl.pathname = "/home";
        const redirectResponse = NextResponse.redirect(homeUrl);
        // Copy cookies over to preserve refreshed sessions
        response.cookies.getAll().forEach((c) => redirectResponse.cookies.set(c));
        return redirectResponse;
    }

    if (isPublicRoute(pathname)) {
        return response;
    }

    if (!user) {
        const signInUrl = request.nextUrl.clone();
        signInUrl.pathname = "/sign-in";
        signInUrl.searchParams.set("redirectedFrom", pathname);
        const redirectResponse = NextResponse.redirect(signInUrl);
        // Copy cookies over to ensure clearing/updating session cookies persists
        response.cookies.getAll().forEach((c) => redirectResponse.cookies.set(c));
        return redirectResponse;
    }

    return response;
}