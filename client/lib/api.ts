import { createClient } from "@/lib/supabase/client";

export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
  const url = path.startsWith("http") ? path : `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;

  return fetch(url, {
    ...options,
    headers,
  });
}
