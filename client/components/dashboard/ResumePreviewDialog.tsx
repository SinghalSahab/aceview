"use client";

import React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, FileText, Award, Layers, Code2, ExternalLink, Calendar, User, Zap } from "lucide-react";
import { ResumeItem } from "@/types/dashboard";

interface ResumePreviewDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  resume: ResumeItem | null;
  onStartInterview: (resume: ResumeItem) => void;
}

export function ResumePreviewDialog({
  isOpen,
  onOpenChange,
  resume,
  onStartInterview,
}: ResumePreviewDialogProps) {
  if (!resume) return null;

  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-2xl translate-x-[-50%] translate-y-[-50%] rounded-2xl bg-zinc-950 border border-zinc-800 p-0 shadow-2xl shadow-purple-950/40 duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 overflow-hidden flex flex-col max-h-[85vh]">
          {/* Header */}
          <div className="px-6 py-5 border-b border-zinc-800 bg-zinc-900/60 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
                <FileText size={20} />
              </div>
              <div>
                <Dialog.Title className="text-base font-bold text-white">
                  {resume.file_name}
                </Dialog.Title>
                <Dialog.Description className="text-xs text-zinc-400">
                  Target Domain: <span className="text-purple-300 font-semibold">{resume.target_role}</span> • ATS: <span className="text-emerald-400 font-semibold">{resume.ats_score}%</span>
                </Dialog.Description>
              </div>
            </div>

            <Dialog.Close asChild>
              <button
                type="button"
                className="w-8 h-8 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white transition"
              >
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 text-zinc-300 text-xs">
            {/* Skills Overview */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                <Code2 size={14} className="text-purple-400" />
                <span>Extracted Technical Skills ({resume.skills?.length || 0})</span>
              </h4>
              <div className="flex flex-wrap gap-1.5 p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800">
                {resume.skills && resume.skills.length > 0 ? (
                  resume.skills.map((s, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 font-medium"
                    >
                      {s}
                    </span>
                  ))
                ) : (
                  <span className="text-zinc-500 italic">No skills extracted</span>
                )}
              </div>
            </div>

            {/* Summary */}
            {resume.summary && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                  Profile Summary
                </h4>
                <div className="p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800 leading-relaxed text-zinc-300">
                  {resume.summary}
                </div>
              </div>
            )}

            {/* Projects / Highlights */}
            {resume.projects && resume.projects.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                  <Layers size={14} className="text-purple-400" />
                  <span>Detected Projects ({resume.projects.length})</span>
                </h4>
                <div className="space-y-2.5">
                  {resume.projects.map((p, idx) => (
                    <div key={idx} className="p-3.5 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-xs">{p.title || `Project ${idx + 1}`}</span>
                        {p.url && (
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-purple-400 hover:underline flex items-center gap-1 text-[11px]"
                          >
                            <span>Link</span>
                            <ExternalLink size={11} />
                          </a>
                        )}
                      </div>
                      {p.description && <p className="text-zinc-400 text-[11px] leading-relaxed">{p.description}</p>}
                      {p.skills && p.skills.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {p.skills.map((tech, tIdx) => (
                            <span key={tIdx} className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                              {tech}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sections Preview */}
            {resume.sections && Object.keys(resume.sections).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                  Detected Resume Sections
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(resume.sections).map(([key, val]) => (
                    <div key={key} className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800">
                      <span className="font-semibold text-purple-300 block">{key}</span>
                      <span className="text-zinc-500 text-[11px] block truncate">{String(val).slice(0, 50)}...</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-zinc-800 bg-zinc-900/60 flex items-center justify-between">
            <Dialog.Close asChild>
              <button
                type="button"
                className="px-4 py-2 rounded-xl border border-zinc-800 text-xs text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
              >
                Close
              </button>
            </Dialog.Close>

            <button
              type="button"
              onClick={() => {
                onOpenChange(false);
                onStartInterview(resume);
              }}
              className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shadow-md shadow-purple-600/30 flex items-center gap-1.5 transition"
            >
              <Zap size={14} className="fill-white" />
              <span>Configure & Start Interview</span>
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
