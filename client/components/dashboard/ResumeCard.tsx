"use client";

import React, { useState } from "react";
import {
  FileText,
  Sparkles,
  Calendar,
  Zap,
  Trash2,
  Eye,
  RefreshCw,
  Github,
  Award,
  ChevronRight,
  Loader2,
  Layers,
} from "lucide-react";
import { ResumeItem } from "@/types/dashboard";

interface ResumeCardProps {
  resume: ResumeItem;
  onStartInterview: (resume: ResumeItem) => void;
  onPreview: (resume: ResumeItem) => void;
  onDelete: (resumeId: string) => Promise<void>;
  onReanalyze?: (resume: ResumeItem) => void;
}

export function ResumeCard({
  resume,
  onStartInterview,
  onPreview,
  onDelete,
  onReanalyze,
}: ResumeCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const formattedDate = new Date(resume.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const atsScore = resume.ats_score || 80;
  const scoreColor =
    atsScore >= 85
      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
      : atsScore >= 70
      ? "text-blue-400 border-blue-500/30 bg-blue-500/10"
      : "text-amber-400 border-amber-500/30 bg-amber-500/10";

  const handleDeleteClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      return;
    }

    try {
      setIsDeleting(true);
      await onDelete(resume.id);
    } catch (err) {
      console.error("Delete error:", err);
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  return (
    <div className="group relative rounded-2xl bg-zinc-950/80 hover:bg-zinc-900/90 border border-zinc-800/80 hover:border-zinc-700/80 p-5 transition-all duration-200 flex flex-col justify-between shadow-lg shadow-black/40 hover:shadow-purple-950/20 backdrop-blur-sm">
      {/* Top row: Icon, title, role, ATS Score */}
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0 group-hover:scale-105 transition">
              <FileText size={20} />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-bold text-white truncate group-hover:text-purple-300 transition" title={resume.file_name}>
                {resume.file_name}
              </h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs font-semibold text-purple-400">
                  {resume.target_role || "Software Engineer"}
                </span>
                {resume.github_username && (
                  <span className="inline-flex items-center gap-1 text-[11px] text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded-md border border-zinc-800">
                    <Github size={11} />
                    <span>@{resume.github_username}</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* ATS Score Indicator */}
          <div
            className={`px-2.5 py-1 rounded-xl border text-xs font-bold shrink-0 flex items-center gap-1.5 shadow-sm ${scoreColor}`}
            title="ATS Readiness & Keyword Calibration Score"
          >
            <Award size={13} />
            <span>{atsScore}% ATS</span>
          </div>
        </div>

        {/* Summary Snippet */}
        {resume.summary && (
          <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed">
            {resume.summary}
          </p>
        )}

        {/* Skills Badges */}
        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-[11px] text-zinc-500 font-medium">
            <span>Parsed Skills</span>
            <span>{resume.skills?.length || 0} detected</span>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-16 overflow-hidden">
            {resume.skills && resume.skills.length > 0 ? (
              <>
                {resume.skills.slice(0, 5).map((skill, idx) => (
                  <span
                    key={idx}
                    className="text-[11px] px-2 py-0.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 font-medium"
                  >
                    {skill}
                  </span>
                ))}
                {resume.skills.length > 5 && (
                  <span className="text-[11px] px-2 py-0.5 rounded-lg bg-purple-950/30 border border-purple-800/40 text-purple-300 font-medium">
                    +{resume.skills.length - 5} more
                  </span>
                )}
              </>
            ) : (
              <span className="text-[11px] text-zinc-600 italic">No skills extracted yet</span>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Metadata & Action Bar */}
      <div className="pt-4 mt-4 border-t border-zinc-800/80 space-y-3">
        <div className="flex items-center justify-between text-[11px] text-zinc-500">
          <span className="flex items-center gap-1">
            <Calendar size={12} />
            {formattedDate}
          </span>

          <div className="flex items-center gap-1.5">
            {/* View Preview */}
            <button
              type="button"
              onClick={() => onPreview(resume)}
              className="p-1.5 rounded-lg bg-zinc-900/80 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition border border-zinc-800"
              title="Preview Parsed Details"
            >
              <Eye size={13} />
            </button>

            {/* Re-analyze */}
            {onReanalyze && (
              <button
                type="button"
                onClick={() => onReanalyze(resume)}
                className="p-1.5 rounded-lg bg-zinc-900/80 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition border border-zinc-800"
                title="Re-analyze Document"
              >
                <RefreshCw size={13} />
              </button>
            )}

            {/* Delete */}
            <button
              type="button"
              disabled={isDeleting}
              onClick={handleDeleteClick}
              className={`p-1.5 rounded-lg transition border text-xs flex items-center gap-1 ${
                showDeleteConfirm
                  ? "bg-rose-500/20 text-rose-300 border-rose-500/40 px-2"
                  : "bg-zinc-900/80 hover:bg-rose-950/30 text-zinc-400 hover:text-rose-400 border-zinc-800 hover:border-rose-800/40"
              }`}
              title={showDeleteConfirm ? "Click again to confirm delete" : "Delete Resume"}
            >
              {isDeleting ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <>
                  <Trash2 size={13} />
                  {showDeleteConfirm && <span>Confirm</span>}
                </>
              )}
            </button>
          </div>
        </div>

        {/* Primary CTA: Start Mock Interview */}
        <button
          type="button"
          onClick={() => onStartInterview(resume)}
          className="w-full h-9 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-950/50 hover:shadow-purple-600/30 transition flex items-center justify-center gap-2 cursor-pointer group/btn"
        >
          <Zap size={14} className="fill-white group-hover/btn:scale-110 transition" />
          <span>Start Mock Interview</span>
          <ChevronRight size={14} className="group-hover/btn:translate-x-0.5 transition" />
        </button>
      </div>
    </div>
  );
}
