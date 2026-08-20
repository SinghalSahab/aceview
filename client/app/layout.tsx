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
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-[#0b0b14] text-white`}>
        <header className="sticky top-0 z-50 flex justify-between items-center px-6 md:px-12 py-3 bg-[#0b0b14]/80 backdrop-blur-md border-b border-white/5 h-16">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <svg viewBox="0 0 32 32" fill="none" className="w-5 h-5">
                <path
                  d="M8 12C8 9.8 9.8 8 12 8H20C22.2 8 24 9.8 24 12V18C24 20.2 22.2 22 20 22H17L13 26V22H12C9.8 22 8 20.2 8 18V12Z"
                  fill="#ffffff"
                />
                <path d="M12 14.5C12 14.5 13.5 13 16 13C18.5 13 20 14.5 20 14.5" stroke="#6c47ff" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M12 17C12 17 13.5 15.5 16 15.5C18.5 15.5 20 17 20 17" stroke="#6c47ff" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </div>
            <span className="font-bold text-xl tracking-tight text-white">Ace<span className="text-purple-400">View</span></span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-neutral-300">
            <Link href="/home" className="hover:text-white transition duration-150">Interviews</Link>
            <Link href="/rag" className="hover:text-white transition duration-150">Resume Analysis</Link>
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <Link
                  href="/home"
                  className="hidden sm:inline-flex text-xs font-semibold bg-purple-600/20 text-purple-300 border border-purple-500/30 px-3.5 py-1.5 rounded-full hover:bg-purple-600/30 transition duration-200"
                >
                  Dashboard
                </Link>
                <UserMenu email={user.email ?? ""} avatarUrl={user.user_metadata?.avatar_url as string | undefined} />
              </div>
            ) : (
              <>
                <Link href="/sign-in">
                  <button className="text-neutral-300 hover:text-white text-sm font-medium px-4 py-2 transition duration-200">
                    Sign In
                  </button>
                </Link>
                <Link href="/sign-up">
                  <button className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-full font-medium text-sm h-9 px-5 transition duration-200 shadow-md shadow-purple-600/20">
                    Get Started
                  </button>
                </Link>
              </>
            )}
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}