import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { UserMenu } from "@/components/auth/UserMenu";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Aceview",
  description: "An AI-powered platform for preparing for mock interviews",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <header className="flex justify-end items-center p-4 gap-4 h-16">
          {user ? (
            <UserMenu email={user.email ?? ""} avatarUrl={user.user_metadata?.avatar_url as string | undefined} />
          ) : (
            <>
              <Link href="/sign-in">
                <button className="bg-[#2e2e2e] text-white rounded-full font-semibold text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-6 hover:bg-[#3a3a3a] transition duration-200 shadow-md">Sign In</button>
              </Link>
              <Link href="/sign-up">
                <button className="bg-[#2e2e2e] text-white rounded-full font-semibold text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-6 hover:bg-[#3a3a3a] transition duration-200 shadow-md">Sign Up</button>
              </Link>
            </>
          )}
        </header>
        {children}
      </body>
    </html>
  );
}