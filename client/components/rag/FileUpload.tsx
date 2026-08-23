"use client";
import React, { useCallback, useEffect, useState } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import { 
  UploadCloud, 
  FileText, 
  X, 
  AlertCircle, 
  Loader2, 
  Eye, 
  EyeOff, 
  Trash2 
} from 'lucide-react';
import { apiFetch } from "@/lib/api";

type FileWithPreview = File & { preview: string };

interface FileUploadProps {
  className?: string;
  dataset: (data: {
    text: string;
    fileName?: string;
    fileSize?: number;
    parsed_details?: any;
    github_profile?: any;
    rawResponse?: any;
  } | null) => void;
}

function FileUpload({ className, dataset }: FileUploadProps) {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [rejected, setRejected] = useState<FileRejection[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [parsedText, setParsedText] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    if (acceptedFiles?.length) {
      setUploadError(null);
      setParsedText(null);
      setShowPreview(false);
      
      setFiles(acceptedFiles.map(file =>
        Object.assign(file, { preview: URL.createObjectURL(file) })
      ) as FileWithPreview[]);
    }

    if (rejectedFiles?.length) {
      setRejected(rejectedFiles);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 10485760, // 10MB
    multiple: false
  });

  useEffect(() => {
    // Revoke the data uris to avoid memory leaks
    return () => files.forEach(file => URL.revokeObjectURL(file.preview));
  }, [files]);

  const removeFile = () => {
    setFiles([]);
    setParsedText(null);
    setUploadError(null);
    setShowPreview(false);
    dataset(null);
  };

  const removeRejected = (name: string) => {
    setRejected(files => files.filter(({ file }) => file.name !== name));
  };

  useEffect(() => {
    if (files.length > 0 && !parsedText && !isUploading) {
      setIsUploading(true);
      setUploadError(null);

      const performUpload = async () => {
        try {
          const formData = new FormData();
          formData.append('file', files[0]);

          const response = await apiFetch("/api/upload", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const errJson = await response.json().catch(() => null);
            throw new Error(errJson?.detail || errJson?.error || `Upload failed (Status: ${response.status})`);
          }

          const data = await response.json();
          setIsUploading(false);
          setParsedText(data.text);
          dataset({
            text: data.text,
            fileName: files[0].name,
            fileSize: files[0].size,
            parsed_details: data.parsed_details,
            github_profile: data.github_profile,
            rawResponse: data,
          });
        } catch (error: any) {
          setIsUploading(false);
          setUploadError(error.message || 'Error uploading file');
          console.error('Error uploading file:', error);
        }
      };

      performUpload();
    }
  }, [files, parsedText, isUploading, dataset]);

  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  return (
    <div className={`flex flex-col gap-6 ${className || ''}`}>
      {/* Dropzone Container */}
      {files.length === 0 && (
        <div className="flex flex-col gap-3">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-8 cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[220px] text-center backdrop-blur-md group
              ${isDragActive 
                ? 'border-purple-500 bg-purple-500/10 shadow-[0_0_20px_rgba(147,51,234,0.15)]' 
                : 'border-white/10 bg-[#13131d]/40 hover:border-purple-500/40 hover:bg-[#13131d]/60 hover:shadow-[0_0_25px_rgba(147,51,234,0.05)]'
              }`}
          >
            <input {...getInputProps()} />
            
            <div className="relative mb-4">
              <div className="absolute -inset-1 rounded-full bg-purple-500/20 blur-md group-hover:bg-purple-500/30 transition duration-300 opacity-0 group-hover:opacity-100" />
              <div className="relative bg-white/5 border border-white/10 rounded-full p-4 group-hover:border-purple-500/30 transition-all duration-300">
                <UploadCloud className="w-8 h-8 text-neutral-400 group-hover:text-purple-400 group-hover:scale-110 transition-all duration-300" />
              </div>
            </div>
            
            <p className="text-sm font-semibold text-neutral-200 group-hover:text-white transition-colors">
              Drag & drop a file here, or <span className="text-purple-400 underline cursor-pointer hover:text-purple-300">browse</span>
            </p>
            <p className="text-xs text-neutral-500 mt-2">
              Supports PDF documents up to 10MB
            </p>
          </div>
        </div>
      )}

      {/* Uploading State */}
      {isUploading && (
        <div className="border border-white/5 bg-[#13131d]/40 backdrop-blur-xl rounded-2xl p-6 flex flex-col items-center justify-center text-center min-h-[180px]">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-4" />
          <p className="text-sm font-medium text-neutral-200">Extracting text from PDF...</p>
          <p className="text-xs text-neutral-500 mt-1">This may take a few seconds depending on document length.</p>
        </div>
      )}

      {/* Upload Error State */}
      {uploadError && (
        <div className="border border-red-500/20 bg-red-500/5 backdrop-blur-xl rounded-2xl p-5 flex flex-col items-center justify-center text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
          <p className="text-sm font-semibold text-red-200">Processing Failed</p>
          <p className="text-xs text-red-400/80 mt-1 mb-4 max-w-xs">{uploadError}</p>
          <button
            type="button"
            onClick={removeFile}
            className="text-xs font-semibold px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-200 border border-red-500/20 rounded-lg transition duration-200 cursor-pointer"
          >
            Reset & Try Again
          </button>
        </div>
      )}

      {/* Success / Uploaded File View */}
      {files.length > 0 && !isUploading && !uploadError && (
        <div className="flex flex-col gap-4">
          <div className="border border-white/10 bg-[#13131d]/60 backdrop-blur-xl rounded-2xl p-4 shadow-xl">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex-shrink-0 bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-red-400">
                  <FileText className="w-6 h-6" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white truncate" title={files[0].name}>
                    {files[0].name}
                  </p>
                  <p className="text-xs text-neutral-400 font-mono mt-0.5">
                    {formatBytes(files[0].size)}
                  </p>
                </div>
              </div>
              
              <button
                type="button"
                onClick={removeFile}
                title="Remove document"
                className="flex-shrink-0 p-1.5 rounded-lg border border-white/5 hover:border-red-500/20 bg-white/5 hover:bg-red-500/10 text-neutral-400 hover:text-red-400 transition-colors cursor-pointer"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                <span className="text-xs font-semibold text-green-400">Parsed & Active</span>
              </div>

              {parsedText && (
                <button
                  type="button"
                  onClick={() => setShowPreview(!showPreview)}
                  className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 font-medium transition-colors cursor-pointer"
                >
                  {showPreview ? (
                    <>
                      <EyeOff className="w-3.5 h-3.5" />
                      <span>Hide Text</span>
                    </>
                  ) : (
                    <>
                      <Eye className="w-3.5 h-3.5" />
                      <span>View Text</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Text Preview Drawer */}
          {showPreview && parsedText && (
            <div className="border border-white/5 bg-black/35 rounded-xl p-4 flex flex-col">
              <div className="flex justify-between items-center mb-2 pb-1.5 border-b border-white/5">
                <span className="text-xs font-semibold text-neutral-300">Extracted PDF Text Preview</span>
                <span className="text-[10px] text-neutral-500 font-mono">
                  {parsedText.length.toLocaleString()} characters
                </span>
              </div>
              <div className="max-h-44 overflow-y-auto text-[11px] text-neutral-400 font-mono leading-relaxed whitespace-pre-wrap select-all scrollbar-thin scrollbar-thumb-white/10 hover:scrollbar-thumb-white/20">
                {parsedText.trim() || "(No readable text extracted)"}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Rejected Files Handling */}
      {rejected.length > 0 && files.length === 0 && (
        <div className="border border-yellow-500/20 bg-yellow-500/5 backdrop-blur-xl rounded-2xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold text-yellow-300">Unsupported Files Rejected</h4>
            <button 
              type="button" 
              onClick={() => setRejected([])} 
              className="text-[10px] uppercase font-bold text-neutral-400 hover:text-white transition duration-200 cursor-pointer"
            >
              Clear
            </button>
          </div>
          <ul className="flex flex-col gap-2">
            {rejected.map(({ file, errors }) => (
              <li key={file.name} className="flex items-start justify-between gap-4 bg-black/20 p-2.5 rounded-lg border border-white/5">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-neutral-200 truncate">{file.name}</p>
                  <ul className="text-[10px] text-red-400 mt-1 list-disc pl-4">
                    {errors.map(error => (
                      <li key={error.code}>{error.message}</li>
                    ))}
                  </ul>
                </div>
                <button
                  type="button"
                  onClick={() => removeRejected(file.name)}
                  className="p-1 rounded bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white transition-colors cursor-pointer"
                >
                  <X className="w-3 h-3" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
