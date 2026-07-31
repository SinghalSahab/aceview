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

    if (isPublicRoute(pathname)) {
        return response;
    }

    if (!user) {
        const signInUrl = request.nextUrl.clone();
        signInUrl.pathname = "/sign-in";
        signInUrl.searchParams.set("redirectedFrom", pathname);
        return NextResponse.redirect(signInUrl);
    }

    return response;
}