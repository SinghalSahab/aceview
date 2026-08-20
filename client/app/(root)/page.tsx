"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Sparkles,
  ArrowRight,
  Bot,
  Brain,
  Code2,
  FileText,
  CheckCircle2,
  TrendingUp,
  Shield,
  Zap,
  Target,
  Play,
  Star,
  ChevronRight,
  Building2,
  Laptop,
  Users,
  Compass,
} from "lucide-react";

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<"technical" | "behavioral" | "system">("technical");

  const tracks = [
    {
      company: "Google",
      initial: "G",
      color: "#ea4335",
      role: "Senior Distributed Systems",
      type: "Technical",
      badge: "High Demand",
      topics: ["Concurrency", "MapReduce", "Consistency Models"],
    },
    {
      company: "Meta",
      initial: "M",
      color: "#0668e1",
      role: "Frontend Architect",
      type: "Technical",
      badge: "Popular",
      topics: ["React 19", "DOM Performance", "State Machines"],
    },
    {
      company: "Amazon",
      initial: "A",
      color: "#ff9900",
      role: "Leadership Principles & System Design",
      type: "Non-Technical",
      badge: "Behavioral",
      topics: ["Customer Obsession", "Scale", "Deliver Results"],
    },
    {
      company: "Netflix",
      initial: "N",
      color: "#e50914",
      role: "Backend & Microservices",
      type: "Technical",
      badge: "Top Rated",
      topics: ["Fault Tolerance", "gRPC", "Caching Strategy"],
    },
  ];

  const features = [
    {
      icon: <Brain className="w-6 h-6 text-purple-400" />,
      title: "Real-Time AI Evaluator",
      description:
        "Get instant, rigorous scoring on problem decomposition, code quality, edge cases, and verbal articulation.",
      tag: "Gemini & LLM Core",
    },
    {
      icon: <FileText className="w-6 h-6 text-indigo-400" />,
      title: "RAG Resume Deep-Dive",
      description:
        "Upload your resume PDF to automatically extract projects, detect skill gaps, and generate tailored questions.",
      tag: "Custom RAG Engine",
    },
    {
      icon: <Code2 className="w-6 h-6 text-cyan-400" />,
      title: "Live Code & Tech Stacks",
      description:
        "Full support for React, TypeScript, Python, Go, Node.js, and modern algorithms with live syntax feedback.",
      tag: "Interactive Sandbox",
    },
    {
      icon: <Target className="w-6 h-6 text-emerald-400" />,
      title: "Company-Specific Rubrics",
      description:
        "Practice against calibrated rubrics from FAANG, high-growth startups, and Fortune 500 hiring committees.",
      tag: "Calibrated Criteria",
    },
  ];

  const stats = [
    { value: "94%", label: "Offer Success Rate", sub: "reported by active candidates" },
    { value: "15,000+", label: "Mock Interviews Completed", sub: "across 40+ engineering roles" },
    { value: "< 2.0s", label: "Instant Feedback Latency", sub: "powered by high-speed AI" },
    { value: "500+", label: "Curated Question Sets", sub: "from top tier tech firms" },
  ];

  const testimonials = [
    {
      quote:
        "AceView's RAG resume prep was a game-changer. It generated questions directly from my past architecture work that Meta actually asked in the loop!",
      author: "David Chen",
      role: "Software Engineer at Meta",
      initials: "DC",
      avatarBg: "bg-blue-600",
    },
    {
      quote:
        "The instant feedback on behavioral and system design answers helped me tighten my STAR stories and eliminate rambling. Landed L5 at Amazon!",
      author: "Priya Sharma",
      role: "Senior Backend Engineer at Amazon",
      initials: "PS",
      avatarBg: "bg-amber-600",
    },
    {
      quote:
        "Practicing with AceView felt just like being in the room with a tough interviewer. The score breakdown showed me exactly which edge cases I overlooked.",
      author: "Alexandre Moreau",
      role: "Frontend Lead at Stripe",
      initials: "AM",
      avatarBg: "bg-purple-600",
    },
  ];

  return (
    <div className="min-h-screen bg-[#0b0b14] text-neutral-100 selection:bg-purple-500/30 selection:text-white">
      {/* Background glow elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-b from-purple-600/20 via-indigo-600/10 to-transparent blur-[140px] rounded-full" />
        <div className="absolute top-[40%] -left-40 w-[500px] h-[500px] bg-purple-900/10 blur-[130px] rounded-full" />
        <div className="absolute top-[60%] -right-40 w-[500px] h-[500px] bg-blue-900/10 blur-[130px] rounded-full" />
      </div>

      <div className="relative z-10">
        {/* ── HERO SECTION ──────────────────────────────────────────────────────── */}
        <section className="px-6 md:px-12 pt-12 md:pt-20 pb-16 max-w-7xl mx-auto">
          <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
            {/* Eyebrow Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md mb-8 hover:border-purple-500/40 transition duration-300">
              <Sparkles className="w-4 h-4 text-purple-400 animate-pulse" />
              <span className="text-xs md:text-sm font-medium text-neutral-200">
                Next-Generation AI Interview & Resume Intelligence
              </span>
              <span className="flex h-1.5 w-1.5 rounded-full bg-purple-400" />
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white leading-[1.12] mb-6">
              Master Every Interview with{" "}
              <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-cyan-400 bg-clip-text text-transparent">
                Precision AI Coaching
              </span>
            </h1>

            {/* Subheading */}
            <p className="text-lg sm:text-xl text-neutral-300 max-w-2xl mx-auto mb-10 leading-relaxed font-normal">
              Practice realistic mock interviews tailored to top tech companies, analyze your resume against job specs, and receive instant, actionable feedback to land your dream offer.
            </p>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
              <Link
                href="/home"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-base px-8 py-4 rounded-full shadow-lg shadow-purple-600/25 hover:shadow-purple-600/40 transition duration-200"
              >
                <span>Start Mock Interview</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/rag"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 text-neutral-200 font-semibold text-base px-8 py-4 rounded-full border border-white/10 hover:border-white/20 transition duration-200 backdrop-blur-md"
              >
                <FileText className="w-4 h-4 text-purple-400" />
                <span>Upload &amp; Analyze Resume</span>
              </Link>
            </div>

            {/* Social Trust Subtext */}
            <div className="mt-8 flex items-center gap-2 text-xs sm:text-sm text-neutral-400">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>No credit card required</span>
              <span className="mx-2 text-neutral-600">•</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Free instant scoring</span>
              <span className="mx-2 text-neutral-600">•</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>FAANG calibrated rubrics</span>
            </div>
          </div>

          {/* ── HERO INTERACTIVE PREVIEW CARD ──────────────────────────────────── */}
          <div className="mt-14 relative mx-auto max-w-5xl">
            {/* Glow frame */}
            <div className="absolute -inset-1 bg-gradient-to-r from-purple-600/30 to-indigo-600/30 rounded-3xl blur-xl opacity-75" />
            
            <div className="relative bg-[#11111f]/90 border border-white/10 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-xl">
              {/* Card Window Topbar */}
              <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/10 bg-white/[0.02]">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
                  <span className="ml-2 text-xs font-mono text-neutral-400">AceView Live Session // Google L5 System Design</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    AI Evaluator Active
                  </span>
                </div>
              </div>

              {/* Card Content Grid */}
              <div className="p-6 md:p-8 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                {/* Left: AI Dialogue & Response */}
                <div className="lg:col-span-7 flex flex-col gap-4">
                  {/* AI Question */}
                  <div className="p-4 rounded-xl bg-white/[0.04] border border-white/5 flex gap-3.5">
                    <div className="w-9 h-9 rounded-lg bg-purple-600/20 border border-purple-500/30 flex items-center justify-center shrink-0">
                      <Bot className="w-5 h-5 text-purple-300" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-purple-300 uppercase tracking-wider">AI Interviewer</span>
                        <span className="text-[11px] text-neutral-400">Technical Round</span>
                      </div>
                      <p className="text-sm text-neutral-200 leading-relaxed font-medium">
                        "Design a distributed rate limiter that handles 500,000 requests/sec with sub-5ms latency across global clusters. How do you handle clock skew between regions?"
                      </p>
                    </div>
                  </div>

                  {/* Candidate Answer Snippet */}
                  <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-500/20 flex gap-3.5">
                    <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                      <Code2 className="w-5 h-5 text-indigo-300" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Your Candidate Answer</span>
                        <span className="text-[11px] text-emerald-400 font-mono">94/100 Strong Match</span>
                      </div>
                      <p className="text-xs sm:text-sm text-neutral-300 font-mono bg-black/30 p-2.5 rounded-lg border border-white/5">
                        Token Bucket algorithm with Redis Cluster + Local in-memory sliding window cache. Synchronized via hybrid logical clocks (HLC) to mitigate NTP drift.
                      </p>
                    </div>
                  </div>

                  {/* Realtime AI Feedback Tags */}
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      ✓ Optimal Concurrency
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                      ✓ Addressed Fault Tolerance
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/20">
                      ★ Suggestion: Detail write-heavy failover
                    </span>
                  </div>
                </div>

                {/* Right: Live Radar Scoring Panel */}
                <div className="lg:col-span-5 bg-black/40 border border-white/5 rounded-xl p-5 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Live Evaluation Rubric</span>
                    <span className="text-xs font-bold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                      Grade: Excellent
                    </span>
                  </div>

                  {/* Metrics */}
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="text-neutral-300">System Architecture</span>
                        <span className="text-purple-300">96%</span>
                      </div>
                      <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
                        <div className="bg-gradient-to-r from-purple-500 to-indigo-500 h-full rounded-full w-[96%]" />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="text-neutral-300">Problem Solving &amp; Edge Cases</span>
                        <span className="text-indigo-300">92%</span>
                      </div>
                      <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-500 to-cyan-500 h-full rounded-full w-[92%]" />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-medium mb-1">
                        <span className="text-neutral-300">Communication &amp; STAR Structure</span>
                        <span className="text-emerald-300">90%</span>
                      </div>
                      <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
                        <div className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full w-[90%]" />
                      </div>
                    </div>
                  </div>

                  {/* Quick CTA */}
                  <Link
                    href="/home"
                    className="mt-2 w-full text-center py-2.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition duration-200 border border-white/10"
                  >
                    Simulate Your Interview →
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── STATS SECTION ────────────────────────────────────────────────────── */}
        <section className="border-y border-white/5 bg-white/[0.01] py-12 px-6 md:px-12">
          <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {stats.map((stat, i) => (
              <div key={i} className="flex flex-col items-center">
                <span className="text-3xl sm:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-100 to-purple-300 mb-1">
                  {stat.value}
                </span>
                <span className="text-sm font-semibold text-neutral-200">{stat.label}</span>
                <span className="text-xs text-neutral-400 mt-0.5">{stat.sub}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── CORE FEATURES ───────────────────────────────────────────────────── */}
        <section className="py-20 px-6 md:px-12 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-semibold uppercase tracking-wider text-purple-400 bg-purple-500/10 px-3 py-1 rounded-full border border-purple-500/20">
              Why AceView
            </span>
            <h2 className="text-3xl sm:text-5xl font-bold text-white mt-4 mb-4 tracking-tight">
              Everything You Need to Crack Any Interview Loop
            </h2>
            <p className="text-neutral-400 text-base sm:text-lg">
              Combining comprehensive interview simulation with document intelligence to give you an unfair advantage.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <div
                key={i}
                className="p-6 rounded-2xl bg-[#13131f] border border-white/5 hover:border-purple-500/30 transition duration-300 flex flex-col justify-between group hover:-translate-y-1 shadow-lg"
              >
                <div>
                  <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-5 group-hover:bg-purple-600/20 group-hover:border-purple-500/40 transition duration-300">
                    {feature.icon}
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
                  <p className="text-sm text-neutral-400 leading-relaxed mb-6">{feature.description}</p>
                </div>
                <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                  <span className="text-[11px] font-medium text-neutral-400">{feature.tag}</span>
                  <ChevronRight className="w-4 h-4 text-neutral-500 group-hover:text-purple-400 transition" />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── COMPANY TRACKS & CATEGORIES ──────────────────────────────────────── */}
        <section className="py-16 px-6 md:px-12 bg-white/[0.01] border-t border-white/5">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full border border-indigo-500/20">
                  Targeted Tracks
                </span>
                <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3">
                  Calibrated for Top Tech Companies
                </h2>
              </div>
              <Link
                href="/home"
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-purple-400 hover:text-purple-300 transition"
              >
                <span>Browse All 50+ Roles</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {tracks.map((track, i) => (
                <div
                  key={i}
                  className="p-6 rounded-2xl bg-[#13131f] border border-white/5 hover:border-white/20 transition duration-200 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div
                        className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-md"
                        style={{ backgroundColor: track.color }}
                      >
                        {track.initial}
                      </div>
                      <span className="text-xs font-medium px-2.5 py-1 rounded-md bg-white/5 text-neutral-300 border border-white/5">
                        {track.badge}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white mb-1">{track.company}</h3>
                    <p className="text-xs text-purple-300 font-medium mb-3">{track.role}</p>

                    <div className="flex flex-wrap gap-1.5 mb-6">
                      {track.topics.map((topic, tidx) => (
                        <span
                          key={tidx}
                          className="text-[11px] bg-white/[0.03] text-neutral-400 px-2 py-0.5 rounded border border-white/5"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>

                  <Link
                    href="/home"
                    className="w-full text-center py-2.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-semibold transition duration-200"
                  >
                    Practice This Track
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── HOW IT WORKS ────────────────────────────────────────────────────── */}
        <section className="py-20 px-6 md:px-12 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full border border-cyan-500/20">
              Workflow
            </span>
            <h2 className="text-3xl sm:text-5xl font-bold text-white mt-4 mb-4 tracking-tight">
              Three Steps from Prep to Offer
            </h2>
            <p className="text-neutral-400 text-base sm:text-lg">
              A structured, repeatable training loop designed by senior engineering interviewers.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            <div className="p-8 rounded-2xl bg-[#11111e] border border-white/5 relative">
              <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/30 text-purple-400 font-bold flex items-center justify-center mb-6 text-base">
                01
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Upload Resume or Pick a Role</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Connect your background with our RAG analyzer, or select from ready-to-go tracks in Frontend, Backend, AI, System Design, or Behavioral rounds.
              </p>
            </div>

            <div className="p-8 rounded-2xl bg-[#11111e] border border-white/5 relative">
              <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-bold flex items-center justify-center mb-6 text-base">
                02
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Interactive Mock Simulation</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Engage in realistic conversational rounds where the AI pushes back, asks for trade-off justifications, and probes for edge cases.
              </p>
            </div>

            <div className="p-8 rounded-2xl bg-[#11111e] border border-white/5 relative">
              <div className="w-10 h-10 rounded-xl bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 font-bold flex items-center justify-center mb-6 text-base">
                03
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Detailed Score &amp; Recommendations</h3>
              <p className="text-sm text-neutral-400 leading-relaxed">
                Get an objective score breakdown, model answers, code optimizations, and customized revision items to lock in readiness.
              </p>
            </div>
          </div>
        </section>

        {/* ── TESTIMONIALS ────────────────────────────────────────────────────── */}
        <section className="py-16 px-6 md:px-12 bg-white/[0.01] border-t border-white/5">
          <div className="max-w-7xl mx-auto">
            <div className="text-center max-w-2xl mx-auto mb-14">
              <h2 className="text-3xl font-bold text-white mb-3">Loved by Engineers Worldwide</h2>
              <p className="text-sm text-neutral-400">Join candidates who converted interviews into top-tier compensation offers.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {testimonials.map((t, idx) => (
                <div key={idx} className="p-6 rounded-2xl bg-[#13131f] border border-white/5 flex flex-col justify-between">
                  <div className="flex gap-1 text-amber-400 mb-4">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 fill-amber-400" />
                    ))}
                  </div>
                  <p className="text-sm text-neutral-300 leading-relaxed italic mb-6">"{t.quote}"</p>
                  <div className="flex items-center gap-3 pt-4 border-t border-white/5">
                    <div className={`w-9 h-9 rounded-full ${t.avatarBg} text-white font-bold text-xs flex items-center justify-center shrink-0`}>
                      {t.initials}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-white">{t.author}</div>
                      <div className="text-xs text-neutral-400">{t.role}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── FINAL CTA BANNER ─────────────────────────────────────────────────── */}
        <section className="py-20 px-6 md:px-12 max-w-6xl mx-auto">
          <div className="relative rounded-3xl overflow-hidden p-8 md:p-14 bg-gradient-to-br from-purple-900/40 via-[#16122d] to-[#0c0c17] border border-purple-500/20 shadow-2xl text-center">
            <div className="max-w-2xl mx-auto relative z-10">
              <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
                Ready to Ace Your Next Tech Interview?
              </h2>
              <p className="text-neutral-300 text-base sm:text-lg mb-8 leading-relaxed">
                Start practicing in under 30 seconds. Sharpen your problem solving, communication, and system design today.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/home"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white text-black hover:bg-neutral-200 font-bold text-base px-8 py-4 rounded-full transition duration-200 shadow-xl"
                >
                  <span>Explore Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/rag"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-purple-600/30 hover:bg-purple-600/40 text-purple-200 font-semibold text-base px-8 py-4 rounded-full border border-purple-500/30 transition duration-200"
                >
                  <FileText className="w-4 h-4" />
                  <span>Resume RAG Chat</span>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ── FOOTER ───────────────────────────────────────────────────────────── */}
        <footer className="border-t border-white/5 py-12 px-6 md:px-12 bg-black/40 text-neutral-400 text-xs">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-md bg-purple-600 flex items-center justify-center text-white font-bold text-xs">
                A
              </div>
              <span className="font-bold text-sm text-white tracking-tight">AceView</span>
              <span className="text-neutral-500 ml-2">© {new Date().getFullYear()} All rights reserved.</span>
            </div>

            <div className="flex items-center gap-6">
              <Link href="/home" className="hover:text-white transition">Interviews</Link>
              <Link href="/rag" className="hover:text-white transition">Resume RAG</Link>
              <Link href="/sign-in" className="hover:text-white transition">Sign In</Link>
              <Link href="/sign-up" className="hover:text-white transition">Sign Up</Link>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}