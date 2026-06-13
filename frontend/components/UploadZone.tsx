"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";

interface Props {
  onFile: (file: File) => void;
  loading: boolean;
  warmingUp: boolean;
}

const MAX_BYTES = 20 * 1024 * 1024;
const ACCEPT_TYPES = ["image/png", "image/jpeg", "image/tiff"];
const ACCEPT_ATTR = ACCEPT_TYPES.join(",");

function formatBytes(b: number): string {
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

interface Preview {
  file: File;
  objectUrl: string;
}

export function UploadZone({ onFile, loading, warmingUp }: Props) {
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /* Revoke object URL on cleanup */
  useEffect(() => {
    const url = preview?.objectUrl;
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [preview?.objectUrl]);

  function stageFile(file: File) {
    if (!ACCEPT_TYPES.includes(file.type)) {
      setValidationError("Only PNG, JPEG, and TIFF files are supported.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setValidationError(`File too large (${formatBytes(file.size)}). Max 20 MB.`);
      return;
    }
    setValidationError(null);
    setPreview((prev) => {
      if (prev?.objectUrl) URL.revokeObjectURL(prev.objectUrl);
      return { file, objectUrl: URL.createObjectURL(file) };
    });
  }

  function clearPreview() {
    setPreview(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) stageFile(file);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Loading state (uploading) ─────────────────────── */
  if (loading) {
    return (
      <div className="card p-6 flex flex-col items-center gap-4 text-center">
        <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center">
          <Spinner size="lg" className="text-indigo-500" />
        </div>

        {warmingUp ? (
          <>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-800">Warming up the model…</p>
              <p className="text-xs text-slate-500 leading-relaxed max-w-[220px] mx-auto">
                The first request after idle can take 30–60 s while the model loads on Render.
              </p>
            </div>
            <div className="progress-track w-full h-1" role="progressbar" aria-label="Loading in progress" aria-valuetext="Indeterminate">
              <div className="progress-thumb" />
            </div>
            <p className="text-[11px] text-slate-400 animate-gentle-pulse">Hang tight — this only happens once per cold start.</p>
          </>
        ) : (
          <>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-800">Processing document…</p>
              <p className="text-xs text-slate-500">Running field extraction</p>
            </div>
            <div className="progress-track w-full h-1" role="progressbar" aria-label="Processing" aria-valuetext="Indeterminate">
              <div className="progress-thumb" />
            </div>
          </>
        )}
      </div>
    );
  }

  /* ── Preview state (file selected, not yet submitted) ─ */
  if (preview) {
    return (
      <div className="card p-4 space-y-4 animate-scale-in">
        {/* Thumbnail */}
        <div
          className="relative rounded-xl overflow-hidden bg-slate-50 border border-slate-100 flex items-center justify-center"
          style={{ minHeight: 160 }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={preview.objectUrl}
            alt={preview.file.name}
            className="max-w-full max-h-52 object-contain"
          />
          <button
            onClick={clearPreview}
            aria-label="Remove selected file"
            className="absolute top-2 right-2 w-7 h-7 rounded-full bg-slate-900/60 hover:bg-slate-900/80 text-white flex items-center justify-center transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* File info */}
        <div className="flex items-center gap-2 text-xs text-slate-500 px-0.5">
          <svg className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="truncate font-medium text-slate-700">{preview.file.name}</span>
          <span className="flex-shrink-0 text-slate-400">{formatBytes(preview.file.size)}</span>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => onFile(preview.file)}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-sm font-semibold py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 outline-none"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Analyze Document
          </button>
          <button
            onClick={clearPreview}
            className="text-sm text-slate-500 hover:text-slate-700 px-3 py-2.5 rounded-xl hover:bg-slate-100 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          >
            Change
          </button>
        </div>
      </div>
    );
  }

  /* ── Idle / drag-over state ────────────────────────── */
  return (
    <div className="space-y-2">
      <label
        className={`
          flex flex-col items-center justify-center w-full cursor-pointer
          border-2 border-dashed rounded-2xl transition-all duration-150
          ${dragging
            ? "border-indigo-400 bg-indigo-50 scale-[1.01]"
            : "border-slate-300 bg-white hover:border-indigo-300 hover:bg-slate-50/70"
          }
        `}
        style={{ minHeight: 200 }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        aria-label="Upload document image"
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) stageFile(file);
          }}
        />

        <div
          className={`flex flex-col items-center gap-3 px-6 py-10 text-center transition-transform duration-150 ${dragging ? "scale-105" : ""}`}
        >
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${dragging ? "bg-indigo-100" : "bg-slate-100"}`}
          >
            <svg
              className={`w-6 h-6 transition-colors ${dragging ? "text-indigo-500" : "text-slate-400"}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>

          {dragging ? (
            <p className="text-sm font-semibold text-indigo-600">Drop to upload</p>
          ) : (
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-700">
                Drag &amp; drop or{" "}
                <span className="text-indigo-600 underline underline-offset-2 decoration-dotted">browse files</span>
              </p>
              <p className="text-xs text-slate-400">PNG, JPEG, TIFF · max 20 MB</p>
            </div>
          )}
        </div>
      </label>

      {validationError && (
        <div
          role="alert"
          className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2.5 animate-fade-up"
        >
          <svg className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs text-red-700">{validationError}</span>
        </div>
      )}
    </div>
  );
}
