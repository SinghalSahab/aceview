import type { Metadata } from "next";
import { Geist, Geist_Mono } from 'next/font/google'
import {
  ClerkProvider,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from '@clerk/nextjs'
import "./globals.css";

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: "Aceview",
  description: "An AI-powered platform for preparing for mock interviews",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
          <header className="flex justify-end items-center p-4 gap-4 h-16">
            <SignedOut>
              <SignInButton >
              <button className="bg-[#2e2e2e] text-white rounded-full font-semibold text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-6 hover:bg-[#3a3a3a] transition duration-200 shadow-md">
                Sign In
              </button>

              </SignInButton>
              <SignUpButton>
                <button className="bg-[#2e2e2e] text-white rounded-full font-semibold text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-6 hover:bg-[#3a3a3a] transition duration-200 shadow-md">
                  Sign Up
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <UserButton />
            </SignedIn>
          </header>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}