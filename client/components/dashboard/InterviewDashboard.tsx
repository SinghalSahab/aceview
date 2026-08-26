"use client";

import React, { useState, useEffect, useCallback, useTransition } from "react";
import {
  FileText,
  UploadCloud,
  Search,
  Sparkles,
  Plus,
  Zap,
  Filter,
  Loader2,
  TrendingUp,
  Brain,
  ShieldCheck,
  RefreshCw,
  FolderOpen,
  ArrowRight,
} from "lucide-react";
import { ResumeCard } from "./ResumeCard";
import { InterviewSetupDialog } from "./InterviewSetupDialog";
import { ResumeUploadModal } from "./ResumeUploadModal";
import { ResumePreviewDialog } from "./ResumePreviewDialog";
import { ResumeItem } from "@/types/dashboard";
import { apiFetch } from "@/lib/api";

export function InterviewDashboard() {
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<string>("all");

  // Dialog & Modal state
  const [selectedResumeForInterview, setSelectedResumeForInterview] = useState<ResumeItem | null>(null);
  const [isInterviewDialogOpen, setIsInterviewDialogOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedResumeForPreview, setSelectedResumeForPreview] = useState<ResumeItem | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // Fetch resumes directly from database API
  const fetchResumes = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiFetch("/api/resumes");
      if (response.ok) {
        const data = await response.json();
        setResumes(data.resumes || []);
      } else {
        setResumes([]);
      }
    } catch (err) {
      console.warn("[Dashboard] Could not fetch resumes from server:", err);
      setResumes([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  const handleDeleteResume = async (resumeId: string) => {
    try {
      await apiFetch(`/api/resumes?id=${resumeId}`, { method: "DELETE" });
      setResumes((prev) => prev.filter((r) => r.id !== resumeId));
    } catch (err) {
      console.error("Failed to delete resume:", err);
      setResumes((prev) => prev.filter((r) => r.id !== resumeId));
    }
  };

  const handleStartInterview = (resume: ResumeItem) => {
    setSelectedResumeForInterview(resume);
    setIsInterviewDialogOpen(true);
  };

  const handlePreviewResume = (resume: ResumeItem) => {
    setSelectedResumeForPreview(resume);
    setIsPreviewOpen(true);
  };

  // Filtering
  const filteredResumes = resumes.filter((r) => {
    const matchesSearch =
      r.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.target_role && r.target_role.toLowerCase().includes(searchQuery.toLowerCase())) ||
      r.skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesRole =
      selectedRoleFilter === "all" ||
      (r.target_role && r.target_role.toLowerCase().includes(selectedRoleFilter.toLowerCase()));

    return matchesSearch && matchesRole;
  });

  const avgAts = resumes.length
    ? Math.round(resumes.reduce((acc, r) => acc + (r.ats_score || 80), 0) / resumes.length)
    : 0;

  return (
    <div className="space-y-8 w-full max-w-7xl mx-auto">
      {/* ── Top Overview & Metrics Bar ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-zinc-950/80 border border-zinc-800/80 shadow-md backdrop-blur-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <FileText size={22} />
          </div>
          <div>
            <span className="text-2xl font-bold text-white tracking-tight">{resumes.length}</span>
            <span className="text-xs text-zinc-400 block font-medium">Uploaded Resumes</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-zinc-950/80 border border-zinc-800/80 shadow-md backdrop-blur-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Zap size={22} />
          </div>
          <div>
            <span className="text-2xl font-bold text-white tracking-tight">Active</span>
            <span className="text-xs text-zinc-400 block font-medium">RAG Question Engine</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-zinc-950/80 border border-zinc-800/80 shadow-md backdrop-blur-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <TrendingUp size={22} />
          </div>
          <div>
            <span className="text-2xl font-bold text-white tracking-tight">{avgAts}%</span>
            <span className="text-xs text-zinc-400 block font-medium">Average ATS Readiness</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-zinc-950/80 border border-zinc-800/80 shadow-md backdrop-blur-sm flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Brain size={22} />
          </div>
          <div>
            <span className="text-2xl font-bold text-white tracking-tight">Dynamic</span>
            <span className="text-xs text-zinc-400 block font-medium">Calibrated Difficulty</span>
          </div>
        </div>
      </div>

      {/* ── Main Section: Header, Controls & Actions ─────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <span>Your Candidate Profiles &amp; Resumes</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-950/40 border border-purple-800/40 text-purple-300">
                {filteredResumes.length}
              </span>
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Select any profile to configure and launch an AI-grounded verbal mock interview.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={fetchResumes}
              disabled={isLoading}
              className="p-2 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 transition disabled:opacity-50"
              title="Refresh Resumes"
            >
              <RefreshCw size={15} className={isLoading ? "animate-spin text-purple-400" : ""} />
            </button>

            <button
              type="button"
              onClick={() => setIsUploadModalOpen(true)}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/30 flex items-center gap-2 transition cursor-pointer"
            >
              <Plus size={16} />
              <span>Upload New Resume</span>
            </button>
          </div>
        </div>

        {/* Search & Filter Strip */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-2 rounded-2xl bg-zinc-950/70 border border-zinc-800/70 backdrop-blur-sm">
          {/* Search Input */}
          <div className="relative w-full sm:w-80">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by resume title, role, or skill..."
              className="w-full h-9 pl-9 pr-3.5 rounded-xl bg-zinc-900/90 border border-zinc-800 text-xs text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-purple-500 focus:border-purple-500 transition"
            />
          </div>

          {/* Role Filter Tabs */}
          <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {[
              { id: "all", label: "All Roles" },
              { id: "full-stack", label: "Full-Stack" },
              { id: "backend", label: "Backend" },
              { id: "frontend", label: "Frontend" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setSelectedRoleFilter(tab.id)}
                className={`text-xs px-3 py-1.5 rounded-lg transition whitespace-nowrap cursor-pointer ${
                  selectedRoleFilter === tab.id
                    ? "bg-purple-600/20 border border-purple-500/40 text-purple-300 font-semibold"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 border border-transparent"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Resume Grid or Empty State ───────────────────────────────────────── */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3 text-zinc-400">
          <Loader2 size={32} className="animate-spin text-purple-500" />
          <span className="text-xs font-medium">Loading candidate profiles...</span>
        </div>
      ) : filteredResumes.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredResumes.map((resume) => (
            <ResumeCard
              key={resume.id}
              resume={resume}
              onStartInterview={handleStartInterview}
              onPreview={handlePreviewResume}
              onDelete={handleDeleteResume}
              onReanalyze={() => setIsUploadModalOpen(true)}
            />
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="rounded-3xl border-2 border-dashed border-zinc-800/80 bg-zinc-950/40 p-12 text-center flex flex-col items-center justify-center space-y-4 max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-purple-400 shadow-inner">
            <FolderOpen size={30} />
          </div>
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-white">No Resumes Found</h3>
            <p className="text-xs text-zinc-400 max-w-xs mx-auto leading-relaxed">
              Upload your resume in PDF or DOCX format to extract skills, calibrate ATS scores, and launch mock interviews.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/30 flex items-center gap-2 transition cursor-pointer"
          >
            <UploadCloud size={16} />
            <span>Upload Your First Resume</span>
          </button>
        </div>
      )}

      {/* ── Dialog Modals ────────────────────────────────────────────────────── */}
      <InterviewSetupDialog
        isOpen={isInterviewDialogOpen}
        onOpenChange={setIsInterviewDialogOpen}
        resume={selectedResumeForInterview}
      />

      <ResumeUploadModal
        isOpen={isUploadModalOpen}
        onOpenChange={setIsUploadModalOpen}
        onUploadSuccess={() => {
          fetchResumes();
        }}
      />

      <ResumePreviewDialog
        isOpen={isPreviewOpen}
        onOpenChange={setIsPreviewOpen}
        resume={selectedResumeForPreview}
        onStartInterview={(res) => {
          setSelectedResumeForInterview(res);
          setIsInterviewDialogOpen(true);
        }}
      />
    </div>
  );
}
