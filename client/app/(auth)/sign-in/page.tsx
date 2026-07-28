"use client";

import { createClient } from "@/lib/supabase/client";

export default function SignIn() {
  const supabase = createClient();

  async function signIn() {
    const { error } = await supabase.auth.signInWithPassword({
      email: "[EMAIL_ADDRESS]",
      password: "[PASSWORD]",
    });

    if (error) {
      console.error(error);
    }
  }

  return (
    <button onClick={signIn}>
      Sign In
    </button>
  );
}