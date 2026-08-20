"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, User as UserIcon } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import Image from "next/image";

type Props = { email: string; avatarUrl?: string | null };

export function UserMenu({ email, avatarUrl }: Props) {
    const [open, setOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const router = useRouter();

    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    async function handleLogout() {
        const supabase = createClient();
        await supabase.auth.signOut();
        router.push("/");
        router.refresh();
    }

    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setOpen((v) => !v)}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-[#2e2e2e] text-white overflow-hidden hover:bg-[#3a3a3a] transition"
                aria-label="User menu"
            >
                {avatarUrl ? (
                    <Image src={avatarUrl} alt={email} className="h-full w-full object-cover" />
                ) : (
                    <UserIcon className="h-5 w-5" />
                )}
            </button>
            {open && (
                <div className="absolute right-0 mt-2 w-48 rounded-md border border-gray-200 bg-white shadow-lg z-50">
                    <div className="px-4 py-2 text-sm text-gray-500 truncate border-b border-gray-100">{email}</div>
                    <button
                        onClick={handleLogout}
                        className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-gray-50 transition"
                    >
                        <LogOut className="h-4 w-4" />
                        Log out
                    </button>
                </div>
            )}
        </div>
    );
}