import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
    const supabase = await createClient();
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error || !user) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();

    const fastapiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
    const backendResponse = await fetch(`${fastapiUrl}/api/upload`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-User-Id": user.id, // trusted here because it only ever reaches
            // FastAPI after the Supabase check above ran
        },
        body: JSON.stringify(body),
    });

    const data = await backendResponse.json();
    return NextResponse.json(data, { status: backendResponse.status });
}