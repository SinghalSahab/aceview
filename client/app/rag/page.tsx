'use client';
import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles } from "lucide-react";
import ChatComponent from "@/components/rag/Chat";
import FileUpload from "@/components/rag/FileUpload";

export default function Home() {
  const [resData, setResData] = useState<{ text: string; fileName?: string; fileSize?: number; } | null>(null);

  const gridBg: React.CSSProperties = {
    backgroundImage:
      "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
    backgroundSize: "40px 40px",
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#0b0b14] text-white flex flex-col relative" style={gridBg}>
      {/* Glow Effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Sub-Header / Navigation */}
      <header className="border-b border-white/5 bg-[#0b0b14]/60 backdrop-blur-md px-6 py-4 flex justify-between items-center z-10">
        <div className="flex items-center gap-4">
          <Link 
            href="/home" 
            className="flex items-center gap-2 text-neutral-400 hover:text-white transition duration-200 text-sm font-medium bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-lg border border-white/5"
          >
            <ArrowLeft size={16} />
            <span>Dashboard</span>
          </Link>
          <div className="h-4 w-[1px] bg-white/10" />
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-purple-400" />
            <h1 className="text-base font-semibold tracking-wide bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-transparent">
              Resume & Prep Doc RAG Chat
            </h1>
          </div>
        </div>
        <div className="text-xs text-neutral-400 font-mono bg-white/5 px-2.5 py-1 rounded border border-white/5">
          v1.0 (Local Backend)
        </div>
      </header>

      {/* Main Split Interface */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-[calc(100vh-8rem)]">
        {/* Left Column: File Upload & Details */}
        <section className="w-full lg:w-[35%] xl:w-[30%] border-r border-white/5 p-6 flex flex-col bg-[#0b0b14]/30 backdrop-blur-sm overflow-y-auto">
          <div className="flex-1 flex flex-col">
            <div className="mb-4">
              <h2 className="text-lg font-bold text-white mb-1">Document Source</h2>
              <p className="text-xs text-neutral-400">
                Upload your resume or preparation guidelines PDF to search and ask questions.
              </p>
            </div>
            <FileUpload 
              className="flex-1" 
              dataset={setResData} 
            />
          </div>
        </section>

        {/* Right Column: Chat Interface */}
        <section className="w-full lg:w-[65%] xl:w-[70%] flex flex-col bg-[#0d0d18]/40 backdrop-blur-sm min-h-[450px] lg:min-h-0">
          <ChatComponent data={resData} />
        </section>
      </main>
    </div>
  );
}

