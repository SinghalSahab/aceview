"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function SignUpPage() {
  const router = useRouter();
  const supabase = createClient();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault();

    const { error } = await supabase.auth.signUp({ email, password });

    if (error) {
      alert(error.message);
      return;
    }

    router.push("/home");
    router.refresh();
  }

  async function handleGoogleSignUp() {
    // Google OAuth has no separate "sign up" step — Supabase creates the
    // user automatically on first login via this provider, so this is the
    // exact same call as the Google button on the sign-in page. The same
    // /auth/callback route handles both.
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=/home`,
      },
    });
  }

  return (
    <div>
      <form onSubmit={handleSignUp}>
        <input type="email" value={email} placeholder="Email" onChange={(e) => setEmail(e.target.value)} />
        <input type="password" value={password} placeholder="Password" onChange={(e) => setPassword(e.target.value)} />
        <button type="submit">Create Account</button>
      </form>

      <button onClick={handleGoogleSignUp}>Sign up with Google</button>
    </div>
  );
}