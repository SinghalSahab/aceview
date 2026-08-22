'use client';
import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles, MessageSquare, Terminal } from "lucide-react";
import ChatComponent from "@/components/rag/Chat";
import FileUpload from "@/components/rag/FileUpload";

/* ==================== TEMPORARY TEST DASHBOARD IMPORT (START) ==================== */
import BackendTestDashboard from "@/components/rag/BackendTestDashboard";
/* ==================== TEMPORARY TEST DASHBOARD IMPORT (END) ==================== */

export default function Home() {
  const [resData, setResData] = useState<any>(null);
  /* ==================== TEMPORARY TEST VIEW STATE (START) ==================== */
  const [activeView, setActiveView] = useState<'chat' | 'test_inspector'>('test_inspector');
  /* ==================== TEMPORARY TEST VIEW STATE (END) ==================== */

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
      <header className="border-b border-white/5 bg-[#0b0b14]/60 backdrop-blur-md px-6 py-4 flex flex-wrap justify-between items-center gap-4 z-10">
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
              AceView Backend Testing & RAG
            </h1>
          </div>
        </div>

        {/* ==================== TEMPORARY TEST VIEW TOGGLE (START) ==================== */}
        <div className="flex items-center gap-2 bg-black/40 p-1 rounded-xl border border-white/10">
          <button
            type="button"
            onClick={() => setActiveView('test_inspector')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              activeView === 'test_inspector'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <Terminal size={14} />
            <span>🔬 Test Inspector (Metrics & Skills)</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveView('chat')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              activeView === 'chat'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            <MessageSquare size={14} />
            <span>💬 RAG Chat</span>
          </button>
        </div>
        {/* ==================== TEMPORARY TEST VIEW TOGGLE (END) ==================== */}
      </header>

      {/* Main Split Interface */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-[calc(100vh-8rem)]">
        {/* Left Column: File Upload & Details */}
        <section className="w-full lg:w-[35%] xl:w-[30%] border-r border-white/5 p-6 flex flex-col bg-[#0b0b14]/30 backdrop-blur-sm overflow-y-auto">
          <div className="flex-1 flex flex-col">
            <div className="mb-4">
              <h2 className="text-lg font-bold text-white mb-1">Document Source</h2>
              <p className="text-xs text-neutral-400">
                Upload your resume PDF to trigger FastAPI text extraction, spaCy skills analysis, and GitHub code metrics.
              </p>
            </div>
            <FileUpload 
              className="flex-1" 
              dataset={setResData} 
            />
          </div>
        </section>

        {/* Right Column: View Panel (Inspector or Chat) */}
        <section className="w-full lg:w-[65%] xl:w-[70%] flex flex-col bg-[#0d0d18]/40 backdrop-blur-sm min-h-[450px] lg:min-h-0 overflow-hidden">
          {/* ==================== TEMPORARY TEST DASHBOARD RENDER (START) ==================== */}
          {activeView === 'test_inspector' ? (
            <BackendTestDashboard data={resData} />
          ) : (
            <ChatComponent data={resData} />
          )}
          {/* ==================== TEMPORARY TEST DASHBOARD RENDER (END) ==================== */}
        </section>
      </main>
    </div>
  );
}


