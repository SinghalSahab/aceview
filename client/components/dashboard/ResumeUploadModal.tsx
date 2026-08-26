"use client";

import React, { useCallback, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useDropzone, FileRejection } from "react-dropzone";
import {
  UploadCloud,
  FileText,
  X,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Sparkles,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ResumeUploadModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onUploadSuccess: (resumeData?: any) => void;
}

export function ResumeUploadModal({
  isOpen,
  onOpenChange,
  onUploadSuccess,
}: ResumeUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<any | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    setError(null);
    setSuccessData(null);

    if (rejectedFiles && rejectedFiles.length > 0) {
      const rej = rejectedFiles[0];
      if (rej.errors[0]?.code === "file-too-large") {
        setError("File exceeds 10MB limit. Please upload a smaller PDF or DOCX document.");
      } else {
        setError(rej.errors[0]?.message || "Invalid file format. Please upload a PDF or DOCX file.");
      }
      return;
    }

    if (acceptedFiles?.length) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/msword": [".doc"],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: false,
  });

  const handleUploadAndParse = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress("Uploading document to ingestion engine...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      setUploadProgress("Running PyMuPDF text extraction & spaCy NLP parsing...");
      const response = await apiFetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => null);
        throw new Error(errJson?.detail || errJson?.error || `Upload failed (Status: ${response.status})`);
      }

      setUploadProgress("Syncing vector chunks into pgvector database...");
      const data = await response.json();
      setSuccessData(data);
      setIsUploading(false);

      // Trigger parent refresh
      onUploadSuccess(data);
    } catch (err: any) {
      console.error("[Resume Upload Error]", err);
      setError(err?.message || "Failed to parse resume document. Please verify the file is text-based.");
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setError(null);
    setSuccessData(null);
    setUploadProgress("");
  };

  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(open) => {
        if (!isUploading) {
          if (!open) handleReset();
          onOpenChange(open);
        }
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] rounded-2xl bg-zinc-950 border border-zinc-800/80 p-0 shadow-2xl shadow-purple-950/40 duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 overflow-hidden">
          {/* Header */}
          <div className="px-6 py-5 border-b border-zinc-800/80 bg-gradient-to-r from-zinc-900/90 via-purple-950/20 to-zinc-900/90 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
                <UploadCloud size={20} />
              </div>
              <div>
                <Dialog.Title className="text-base font-bold text-white tracking-tight">
                  Upload & Analyze Resume
                </Dialog.Title>
                <Dialog.Description className="text-xs text-zinc-400">
                  AI extracts skills, projects, and generates tailored interview question banks.
                </Dialog.Description>
              </div>
            </div>

            <Dialog.Close asChild>
              <button
                type="button"
                disabled={isUploading}
                className="w-8 h-8 rounded-lg bg-zinc-900/80 hover:bg-zinc-800 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white transition disabled:opacity-50"
              >
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          <div className="p-6 space-y-5">
            {error && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5">
                <AlertCircle size={16} className="text-rose-400 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {successData ? (
              <div className="py-6 text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 mx-auto flex items-center justify-center shadow-lg shadow-emerald-500/20">
                  <CheckCircle2 size={32} />
                </div>
                <div className="space-y-1.5">
                  <h3 className="text-sm font-bold text-white">Resume Ingested & Analyzed!</h3>
                  <p className="text-xs text-zinc-400 max-w-sm mx-auto">
                    Successfully extracted{" "}
                    <span className="text-purple-300 font-semibold">
                      {successData?.parsed_details?.skills?.length || 0} skills
                    </span>{" "}
                    and calibrated candidate vector chunks.
                  </p>
                </div>

                <div className="pt-3 flex justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      handleReset();
                      onOpenChange(false);
                    }}
                    className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/30 transition flex items-center gap-1.5"
                  >
                    <span>View in Dashboard</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Dropzone Area */}
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 ${
                    isDragActive
                      ? "border-purple-500 bg-purple-950/20 scale-[0.99]"
                      : file
                      ? "border-emerald-500/50 bg-emerald-950/10"
                      : "border-zinc-800 hover:border-zinc-700 bg-zinc-900/40 hover:bg-zinc-900/80"
                  }`}
                >
                  <input {...getInputProps()} />

                  {file ? (
                    <div className="flex flex-col items-center space-y-2">
                      <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                        <FileText size={24} />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-white">{file.name}</p>
                        <p className="text-[11px] text-zinc-400 mt-0.5">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for parsing
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                        className="text-[11px] text-rose-400 hover:underline pt-1"
                      >
                        Choose a different file
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800 text-purple-400 flex items-center justify-center shadow-inner">
                        <UploadCloud size={24} />
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-semibold text-zinc-200">
                          {isDragActive ? "Drop the resume here..." : "Drag and drop your resume file here"}
                        </p>
                        <p className="text-[11px] text-zinc-500">
                          Supports PDF or DOCX format (Max 10MB)
                        </p>
                      </div>
                      <span className="text-[11px] font-medium text-purple-400 bg-purple-600/10 px-3 py-1 rounded-full border border-purple-500/20">
                        Browse Files
                      </span>
                    </>
                  )}
                </div>

                {/* Progress / Actions */}
                {isUploading ? (
                  <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-3">
                    <div className="flex items-center gap-2.5 text-xs text-purple-300 font-medium">
                      <Loader2 size={16} className="animate-spin text-purple-400 shrink-0" />
                      <span>{uploadProgress}</span>
                    </div>
                    <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-gradient-to-r from-purple-500 to-indigo-500 h-full w-2/3 animate-pulse" />
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => onOpenChange(false)}
                      className="px-4 py-2 rounded-xl border border-zinc-800 text-xs font-medium text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={!file}
                      onClick={handleUploadAndParse}
                      className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/20 transition disabled:opacity-50 cursor-pointer flex items-center gap-2"
                    >
                      <Sparkles size={14} />
                      <span>Ingest & Parse Resume</span>
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
