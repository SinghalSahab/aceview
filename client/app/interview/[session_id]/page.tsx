"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Mic,
  MicOff,
  PhoneOff,
  Sparkles,
  ArrowLeft,
  Volume2,
  Bot,
  Brain,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Terminal,
  Activity,
  Layers,
} from "lucide-react";

export default function InterviewSessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.session_id as string;

  const [isMuted, setIsMuted] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "live" | "evaluating">("connecting");
  const [messages, setMessages] = useState<
    Array<{ sender: "ai" | "user"; text: string; timestamp: string }>
  >([
    {
      sender: "ai",
      text: "Hello! Welcome to your verbal mock interview. I have reviewed your candidate profile and technical projects. Whenever you're ready, let's start with a high-level overview of the most complex system architecture you designed recently.",
      timestamp: "Just now",
    },
  ]);

  // Timer simulation
  useEffect(() => {
    const timer = setInterval(() => {
      setSessionTime((prev) => prev + 1);
    }, 1000);

    const connTimer = setTimeout(() => {
      setConnectionStatus("live");
    }, 1500);

    return () => {
      clearInterval(timer);
      clearTimeout(connTimer);
    };
  }, []);

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#0b0b14] text-white flex flex-col relative overflow-hidden">
      {/* Glow Effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Header bar */}
      <header className="px-6 py-4 border-b border-white/5 bg-[#0b0b14]/70 backdrop-blur-md flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <Link
            href="/home"
            className="flex items-center gap-2 text-xs font-semibold text-zinc-400 hover:text-white bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 px-3 py-1.5 rounded-xl transition"
          >
            <ArrowLeft size={14} />
            <span>Dashboard</span>
          </Link>

          <div className="h-4 w-[1px] bg-white/10" />

          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-bold text-white tracking-wide">
              LIVE MOCK INTERVIEW
            </span>
            <span className="text-[11px] font-mono text-zinc-500 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
              ID: {sessionId?.slice(0, 8)}...
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-mono bg-zinc-900/80 border border-zinc-800 px-3 py-1.5 rounded-xl text-zinc-300">
            <Clock size={13} className="text-purple-400" />
            <span>{formatSeconds(sessionTime)}</span>
          </div>

          <button
            type="button"
            onClick={() => router.push("/home")}
            className="flex items-center gap-1.5 text-xs font-bold bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 px-3.5 py-1.5 rounded-xl transition"
          >
            <PhoneOff size={13} />
            <span>End Session</span>
          </button>
        </div>
      </header>

      {/* Main Live Interface */}
      <main className="flex-1 flex flex-col lg:flex-row p-6 gap-6 max-w-7xl w-full mx-auto overflow-hidden">
        {/* Left: Interactive AI Avatar & Audio Visualizer */}
        <section className="w-full lg:w-1/2 flex flex-col items-center justify-center p-8 rounded-3xl bg-zinc-950/60 border border-zinc-800/70 shadow-2xl backdrop-blur-sm relative space-y-8">
          <div className="relative">
            {/* Pulsing rings */}
            <div className="absolute -inset-4 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 opacity-20 blur-xl animate-pulse" />
            <div className="w-36 h-36 rounded-full bg-gradient-to-tr from-purple-900 to-zinc-900 border-2 border-purple-500/50 flex items-center justify-center shadow-2xl shadow-purple-900/40 relative">
              <Bot size={64} className="text-purple-300 animate-pulse" />
            </div>
          </div>

          {/* Status badge */}
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/40 border border-purple-800/40 text-purple-300 text-xs font-semibold">
              <Activity size={13} className="animate-spin text-purple-400" />
              <span>AI Interviewer Active & Listening</span>
            </div>
            <h2 className="text-lg font-bold text-white">Verbal Dialogue Grounded in RAG Profile</h2>
            <p className="text-xs text-zinc-400 max-w-sm">
              Speak naturally into your microphone. The AI evaluates depth, system trade-offs, and communication clarity.
            </p>
          </div>

          {/* Voice Audio Controls */}
          <div className="flex items-center gap-4 pt-4">
            <button
              type="button"
              onClick={() => setIsMuted(!isMuted)}
              className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg transition cursor-pointer ${
                isMuted
                  ? "bg-rose-500 text-white shadow-rose-600/30"
                  : "bg-purple-600 hover:bg-purple-500 text-white shadow-purple-600/30"
              }`}
              title={isMuted ? "Unmute Microphone" : "Mute Microphone"}
            >
              {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
            </button>

            <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl bg-zinc-900 border border-zinc-800 text-xs text-zinc-300">
              <Volume2 size={16} className="text-purple-400 animate-bounce" />
              <span>Speech-to-Text Active</span>
            </div>
          </div>
        </section>

        {/* Right: Live Transcript & Candidate Grounding */}
        <section className="w-full lg:w-1/2 flex flex-col rounded-3xl bg-zinc-950/60 border border-zinc-800/70 p-6 backdrop-blur-sm overflow-hidden">
          <div className="flex items-center justify-between pb-4 border-b border-zinc-800/80">
            <div className="flex items-center gap-2 text-xs font-bold text-zinc-300 uppercase tracking-wider">
              <Terminal size={15} className="text-purple-400" />
              <span>Live Dialogue & Evaluation Stream</span>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">Turn 1 of 6</span>
          </div>

          {/* Messages stream */}
          <div className="flex-1 overflow-y-auto py-4 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-2xl border text-xs leading-relaxed space-y-1.5 ${
                  msg.sender === "ai"
                    ? "bg-purple-950/20 border-purple-500/30 text-zinc-200"
                    : "bg-zinc-900/80 border-zinc-800 text-white ml-8"
                }`}
              >
                <div className="flex items-center justify-between font-bold text-[11px]">
                  <span className={msg.sender === "ai" ? "text-purple-300" : "text-cyan-300"}>
                    {msg.sender === "ai" ? "AceView Evaluator (AI)" : "Candidate (You)"}
                  </span>
                  <span className="text-zinc-500 text-[10px] font-normal">{msg.timestamp}</span>
                </div>
                <p>{msg.text}</p>
              </div>
            ))}
          </div>

          {/* Quick evaluation notes */}
          <div className="pt-4 border-t border-zinc-800/80 flex items-center justify-between text-[11px] text-zinc-400">
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-400" />
              <span>Auto-rubric: STAR scoring active</span>
            </div>
            <span className="text-purple-400 font-medium">Difficulty Level: 2 (Standard)</span>
          </div>
        </section>
      </main>
    </div>
  );
}
