"use client";

import React, { useState, useTransition, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import {
  X,
  Sparkles,
  Flame,
  Clock,
  Code2,
  Users,
  Layers,
  ChevronRight,
  Loader2,
  CheckCircle2,
  Bot,
  BrainCircuit,
  Sliders,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { ResumeItem, InterviewType, DifficultyLevel, InterviewConfig } from "@/types/dashboard";

interface InterviewSetupDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  resume: ResumeItem | null;
}

const INTERVIEW_TYPES: Array<{
  id: InterviewType;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}> = [
  {
    id: "technical",
    title: "Technical Deep Dive",
    subtitle: "Project architecture, coding trade-offs, algorithms & system internals",
    icon: Code2,
    accentColor: "from-cyan-500 to-blue-600",
  },
  {
    id: "behavioral",
    title: "Behavioral & Leadership",
    subtitle: "STAR method evaluation, conflict resolution, ownership & team dynamics",
    icon: Users,
    accentColor: "from-purple-500 to-indigo-600",
  },
  {
    id: "mixed",
    title: "Mixed Comprehensive",
    subtitle: "Full-loop standard mock covering system design, live code, & culture fit",
    icon: Layers,
    accentColor: "from-emerald-500 to-teal-600",
  },
];

const DIFFICULTY_LEVELS: Array<{
  level: DifficultyLevel;
  label: string;
  badge: string;
  description: string;
  color: string;
}> = [
  {
    level: 1,
    label: "Level 1: Foundations",
    badge: "Junior / Warm-up",
    description: "Core syntax, common design patterns, and foundational concepts.",
    color: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  },
  {
    level: 2,
    label: "Level 2: Standard",
    badge: "Mid-Level (Default)",
    description: "Production architectural choices, real-world edge cases, and API design.",
    color: "border-blue-500/40 bg-blue-500/10 text-blue-300",
  },
  {
    level: 3,
    label: "Level 3: Senior",
    badge: "Senior Engineer",
    description: "High-scale trade-offs, performance optimization, resilience, & debugging.",
    color: "border-purple-500/40 bg-purple-500/10 text-purple-300",
  },
  {
    level: 4,
    label: "Level 4: Staff",
    badge: "Staff / Principal",
    description: "Cross-system consistency, extreme concurrency, and ambiguous problem spaces.",
    color: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  },
];

const FOCUS_AREA_OPTIONS = [
  "System Design",
  "Concurrency & DBs",
  "API Design & REST/gRPC",
  "Testing & CI/CD",
  "Framework Internals",
  "Distributed Caching",
  "Security & Auth",
  "Microservices",
];

const ROLE_SUGGESTIONS = [
  "Full-Stack Engineer",
  "Backend Python / FastAPI",
  "Distributed Systems Architect",
  "Frontend React & Next.js",
  "Cloud & DevOps Engineer",
  "AI / ML Infrastructure",
];

export function InterviewSetupDialog({
  isOpen,
  onOpenChange,
  resume,
}: InterviewSetupDialogProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  // Form State
  const [targetRole, setTargetRole] = useState("");
  const [interviewType, setInterviewType] = useState<InterviewType>("technical");
  const [difficulty, setDifficulty] = useState<DifficultyLevel>(2);
  const [focusAreas, setFocusAreas] = useState<string[]>(["System Design", "API Design & REST/gRPC"]);
  const [duration, setDuration] = useState<15 | 30 | 45>(30);

  // Launching Progress Steps
  const [launchStep, setLaunchStep] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Pre-fill role from selected resume
  useEffect(() => {
    if (resume) {
      setTargetRole(resume.target_role || "Full-Stack Engineer");
      setErrorMessage(null);
      setLaunchStep(0);
    }
  }, [resume, isOpen]);

  const toggleFocusArea = (area: string) => {
    setFocusAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  };

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resume) return;

    if (!targetRole.trim()) {
      setErrorMessage("Please specify a target role or domain.");
      return;
    }

    setErrorMessage(null);
    setLaunchStep(1);

    const payload: InterviewConfig = {
      resume_id: resume.id,
      target_role: targetRole.trim(),
      interview_type: interviewType,
      difficulty,
      focus_areas: focusAreas,
      duration,
    };

    try {
      // Step 1: Initializing context
      setLaunchStep(1);
      await new Promise((resolve) => setTimeout(resolve, 600));

      // Step 2: Grounding agent
      setLaunchStep(2);
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Send session initialization request
      const response = await apiFetch("/api/interviews/session", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.error || `Failed to create interview session (${response.status})`);
      }

      const data = await response.json();
      const sessionId = data.session_id || "mock-session-1";

      // Step 3: Calibrated loop ready
      setLaunchStep(3);
      await new Promise((resolve) => setTimeout(resolve, 500));

      startTransition(() => {
        onOpenChange(false);
        router.push(`/interview/${sessionId}`);
      });
    } catch (err: any) {
      console.error("[Launch Interview Error]", err);
      setErrorMessage(err.message || "Failed to launch interview session. Please try again.");
      setLaunchStep(0);
    }
  };

  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-2xl translate-x-[-50%] translate-y-[-50%] rounded-2xl bg-zinc-950 border border-zinc-800/80 p-0 shadow-2xl shadow-purple-950/40 duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 overflow-hidden flex flex-col max-h-[92vh]">
          {/* Header Banner */}
          <div className="relative px-6 py-5 border-b border-zinc-800/80 bg-gradient-to-r from-zinc-900/90 via-purple-950/20 to-zinc-900/90 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-md shadow-purple-950/50">
                <Sparkles size={20} />
              </div>
              <div>
                <Dialog.Title className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  Configure Mock Interview
                  {resume && (
                    <span className="text-xs font-normal px-2.5 py-0.5 rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300">
                      {resume.file_name}
                    </span>
                  )}
                </Dialog.Title>
                <Dialog.Description className="text-xs text-zinc-400">
                  Calibrate the AI interviewer to test specific skills, difficulty, and focus areas.
                </Dialog.Description>
              </div>
            </div>

            <Dialog.Close asChild>
              <button
                type="button"
                disabled={launchStep > 0}
                className="w-8 h-8 rounded-lg bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white transition disabled:opacity-50"
              >
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          {/* Form Content / Scrollable Area */}
          <form onSubmit={handleLaunch} className="flex-1 overflow-y-auto px-6 py-5 space-y-6 text-zinc-200">
            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <ShieldCheck size={16} className="text-rose-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Launch In-Progress Loading State */}
            {launchStep > 0 ? (
              <div className="py-12 px-4 flex flex-col items-center justify-center text-center space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 rounded-full bg-purple-600/20 border-2 border-purple-500/40 flex items-center justify-center shadow-lg shadow-purple-600/30 animate-pulse">
                    <Bot size={36} className="text-purple-400 animate-bounce" />
                  </div>
                  <Loader2 size={88} className="absolute inset-0 -top-1 -left-1 text-purple-500 animate-spin" />
                </div>

                <div className="space-y-2 max-w-sm">
                  <h3 className="text-base font-semibold text-white">
                    {launchStep === 1 && "Initializing Candidate Context..."}
                    {launchStep === 2 && "Grounding Agent with Resume & GitHub RAG..."}
                    {launchStep === 3 && "Calibrated Question Loop Ready!"}
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Preparing real-time evaluator, scoring rubrics, and dynamic difficulty bounds for{" "}
                    <strong className="text-zinc-200">{targetRole}</strong>.
                  </p>
                </div>

                {/* Progress Indicators */}
                <div className="w-full max-w-xs space-y-2 text-left">
                  <div className="flex items-center gap-2.5 text-xs">
                    {launchStep >= 1 ? (
                      <CheckCircle2 size={14} className="text-emerald-400" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-zinc-700" />
                    )}
                    <span className={launchStep >= 1 ? "text-zinc-200 font-medium" : "text-zinc-500"}>
                      Parsed profile & technical skills ingested
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5 text-xs">
                    {launchStep >= 2 ? (
                      <CheckCircle2 size={14} className="text-emerald-400" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-zinc-700" />
                    )}
                    <span className={launchStep >= 2 ? "text-zinc-200 font-medium" : "text-zinc-500"}>
                      Vector similarity index calibrated (pgvector)
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5 text-xs">
                    {launchStep >= 3 ? (
                      <CheckCircle2 size={14} className="text-emerald-400" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-zinc-700" />
                    )}
                    <span className={launchStep >= 3 ? "text-zinc-200 font-medium" : "text-zinc-500"}>
                      Starting dynamic interview session
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* 1. Target Role / Domain */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                    <span>1. Target Role / Domain</span>
                    <span className="text-[11px] font-normal text-zinc-500">Editable</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                    placeholder="e.g. Senior Full-Stack Engineer, Backend Python, System Architect"
                    className="w-full h-10 px-3.5 rounded-xl bg-zinc-900/90 border border-zinc-800 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition"
                  />
                  {/* Quick role suggestions */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {ROLE_SUGGESTIONS.map((role) => (
                      <button
                        key={role}
                        type="button"
                        onClick={() => setTargetRole(role)}
                        className={`text-[11px] px-2.5 py-1 rounded-lg border transition ${
                          targetRole === role
                            ? "bg-purple-600/20 border-purple-500/40 text-purple-300 font-medium"
                            : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                        }`}
                      >
                        {role}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 2. Interview Type Selection */}
                <div className="space-y-2.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    2. Interview Track / Type
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    {INTERVIEW_TYPES.map((type) => {
                      const Icon = type.icon;
                      const isSelected = interviewType === type.id;
                      return (
                        <button
                          key={type.id}
                          type="button"
                          onClick={() => setInterviewType(type.id)}
                          className={`p-3.5 rounded-xl border text-left transition relative flex flex-col justify-between group cursor-pointer ${
                            isSelected
                              ? "bg-purple-950/30 border-purple-500/60 shadow-md shadow-purple-950/40"
                              : "bg-zinc-900/60 border-zinc-800/80 hover:bg-zinc-900 hover:border-zinc-700"
                          }`}
                        >
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <div
                                className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                  isSelected
                                    ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                                    : "bg-zinc-800 text-zinc-400"
                                }`}
                              >
                                <Icon className="w-4 h-4" />
                              </div>
                              {isSelected && (
                                <div className="w-2 h-2 rounded-full bg-purple-400 shadow-sm shadow-purple-400" />
                              )}
                            </div>
                            <div>
                              <h4 className="text-xs font-bold text-white">{type.title}</h4>
                              <p className="text-[11px] text-zinc-400 mt-1 leading-snug">{type.subtitle}</p>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 3. Starting Difficulty Level */}
                <div className="space-y-2.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                    <span>3. Starting Difficulty Level</span>
                    <span className="text-[11px] font-normal text-purple-400">AI dynamically scales mid-session</span>
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {DIFFICULTY_LEVELS.map((diff) => {
                      const isSelected = difficulty === diff.level;
                      return (
                        <button
                          key={diff.level}
                          type="button"
                          onClick={() => setDifficulty(diff.level)}
                          className={`p-3 rounded-xl border text-left transition flex flex-col justify-between cursor-pointer ${
                            isSelected
                              ? `${diff.color} shadow-md`
                              : "bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:bg-zinc-900 hover:border-zinc-700 hover:text-zinc-200"
                          }`}
                        >
                          <div>
                            <span className="text-xs font-bold block">{diff.badge}</span>
                            <span className="text-[10px] opacity-75 mt-0.5 block">{diff.label}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 4. Target Focus Areas (Multi-select) */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center justify-between">
                    <span>4. Focus Areas (Optional Multi-Select)</span>
                    <span className="text-[11px] font-normal text-zinc-500">
                      {focusAreas.length} selected
                    </span>
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {FOCUS_AREA_OPTIONS.map((area) => {
                      const isSelected = focusAreas.includes(area);
                      return (
                        <button
                          key={area}
                          type="button"
                          onClick={() => toggleFocusArea(area)}
                          className={`text-xs px-3 py-1.5 rounded-lg border transition flex items-center gap-1.5 cursor-pointer ${
                            isSelected
                              ? "bg-purple-600/20 border-purple-500/40 text-purple-200 font-medium"
                              : "bg-zinc-900/80 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? "bg-purple-400" : "bg-zinc-600"}`} />
                          {area}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 5. Session Duration */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    5. Session Duration
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { mins: 15, label: "15 mins", sub: "Quick Screen (3-4 Qs)" },
                      { mins: 30, label: "30 mins", sub: "Standard Loop (6-8 Qs)" },
                      { mins: 45, label: "45 mins", sub: "Comprehensive Deep Dive" },
                    ].map((d) => (
                      <button
                        key={d.mins}
                        type="button"
                        onClick={() => setDuration(d.mins as any)}
                        className={`p-2.5 rounded-xl border text-center transition cursor-pointer ${
                          duration === d.mins
                            ? "bg-purple-600/20 border-purple-500/50 text-purple-200 font-semibold"
                            : "bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:bg-zinc-900 hover:border-zinc-700"
                        }`}
                      >
                        <div className="text-xs font-bold">{d.label}</div>
                        <div className="text-[10px] text-zinc-400 mt-0.5">{d.sub}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Footer / CTA Actions */}
            {launchStep === 0 && (
              <div className="pt-4 border-t border-zinc-800/80 flex items-center justify-between gap-4">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="px-4 py-2.5 rounded-xl border border-zinc-800 text-xs font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
                  >
                    Cancel
                  </button>
                </Dialog.Close>

                <button
                  type="submit"
                  disabled={isPending || !targetRole.trim()}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-600/30 flex items-center gap-2 transition cursor-pointer disabled:opacity-50"
                >
                  <Zap size={14} className="fill-white" />
                  <span>Launch Verbal Interview</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            )}
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
