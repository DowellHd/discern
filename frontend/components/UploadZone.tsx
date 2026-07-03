"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Spinner } from "@/components/ui/Spinner";

const MAX_BYTES = 20 * 1024 * 1024;
const ACCEPT_TYPES = ["image/png", "image/jpeg", "image/tiff", "application/pdf"];
const ACCEPT_ATTR = ACCEPT_TYPES.join(",");
const FORMAT_LABELS = ["PNG", "JPEG", "TIFF", "PDF"];

function formatBytes(b: number): string {
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

interface Preview {
  file: File;
  objectUrl: string | null;
}

function PdfIcon() {
  return (
    <svg className="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

// ── Single-file mode ──────────────────────────────────────────────────────────

interface SingleProps {
  mode: "single";
  onFile: (file: File) => void;
  onStage?: (file: File | null) => void;
  loading: boolean;
  warmingUp: boolean;
}

function SingleUploadZone({ onFile, onStage, loading, warmingUp }: Omit<SingleProps, "mode">) {
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const url = preview?.objectUrl;
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [preview?.objectUrl]);

  function stageFile(file: File) {
    if (!ACCEPT_TYPES.includes(file.type)) {
      setValidationError("Only PNG, JPEG, TIFF, and PDF files are supported.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setValidationError(`File too large (${formatBytes(file.size)}). Max 20 MB.`);
      return;
    }
    setValidationError(null);
    setPreview((prev) => {
      if (prev?.objectUrl) URL.revokeObjectURL(prev.objectUrl);
      const objectUrl = file.type === "application/pdf" ? null : URL.createObjectURL(file);
      return { file, objectUrl };
    });
    onStage?.(file);
  }

  function clearPreview() {
    setPreview(null);
    setValidationError(null);
    onStage?.(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) stageFile(file);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
            <div className="progress-track w-full h-1" role="progressbar" aria-label="Loading" aria-valuetext="Indeterminate">
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

  if (preview) {
    return (
      <div className="card p-4 space-y-4 animate-scale-in">
        <div
          className="relative rounded-xl overflow-hidden bg-slate-50 border border-slate-100 flex items-center justify-center"
          style={{ minHeight: 160 }}
        >
          {preview.objectUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={preview.objectUrl}
              alt={preview.file.name}
              className="max-w-full max-h-52 object-contain"
            />
          ) : (
            <div className="flex flex-col items-center gap-2 py-6">
              <PdfIcon />
              <span className="text-xs font-semibold text-slate-500">PDF — page 1 will be extracted</span>
            </div>
          )}
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

        <div className="flex items-center gap-2 text-xs text-slate-500 px-0.5">
          <svg className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="truncate font-medium text-slate-700">{preview.file.name}</span>
          <span className="flex-shrink-0 text-slate-400">{formatBytes(preview.file.size)}</span>
        </div>

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

  return (
    <div className="space-y-2">
      <label
        className="block w-full cursor-pointer rounded-2xl transition-all duration-200"
        style={{
          background: dragging ? "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)" : "#ffffff",
          border: dragging ? "2px dashed #6366f1" : "2px dashed #cbd5e1",
          transform: dragging ? "scale(1.01)" : "scale(1)",
          boxShadow: dragging ? "0 8px 24px rgba(99,102,241,0.15)" : "0 1px 3px rgba(0,0,0,0.06)",
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        aria-label="Upload document"
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          className="sr-only"
          onChange={(e) => { const file = e.target.files?.[0]; if (file) stageFile(file); }}
        />
        <DropZoneContent dragging={dragging} />
      </label>

      {validationError && <ValidationError message={validationError} />}
    </div>
  );
}

// ── Batch-file mode ───────────────────────────────────────────────────────────

interface BatchProps {
  mode: "batch";
  onFiles: (files: File[]) => void;
  loading: boolean;
  initialFiles?: File[];
}

function BatchUploadZone({ onFiles, loading, initialFiles }: Omit<BatchProps, "mode">) {
  const [dragging, setDragging] = useState(false);
  const [staged, setStaged] = useState<File[]>(initialFiles ?? []);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(incoming: FileList | File[]) {
    const files = Array.from(incoming);
    const bad = files.find((f) => !ACCEPT_TYPES.includes(f.type));
    if (bad) { setValidationError(`Unsupported type: ${bad.name}`); return; }
    const oversized = files.find((f) => f.size > MAX_BYTES);
    if (oversized) { setValidationError(`File too large: ${oversized.name}`); return; }
    setValidationError(null);
    setStaged((prev) => {
      const names = new Set(prev.map((f) => f.name));
      return [...prev, ...files.filter((f) => !names.has(f.name))];
    });
  }

  function removeFile(idx: number) {
    setStaged((prev) => prev.filter((_, i) => i !== idx));
  }

  function clearAll() {
    setStaged([]);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="card p-6 flex flex-col items-center gap-4 text-center">
        <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center">
          <Spinner size="lg" className="text-indigo-500" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-800">Processing {staged.length} documents…</p>
          <p className="text-xs text-slate-500">Running field extraction on each file</p>
        </div>
        <div className="progress-track w-full h-1" role="progressbar" aria-label="Processing batch" aria-valuetext="Indeterminate">
          <div className="progress-thumb" />
        </div>
      </div>
    );
  }

  if (staged.length > 0) {
    return (
      <div className="card p-4 space-y-3 animate-scale-in">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
            {staged.length} file{staged.length !== 1 ? "s" : ""} staged
          </span>
          <button
            onClick={clearAll}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
          >
            Clear all
          </button>
        </div>

        <ul className="space-y-1.5 max-h-48 overflow-y-auto">
          {staged.map((f, i) => (
            <li key={f.name} className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-slate-50 text-xs">
              <svg className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="truncate font-medium text-slate-700 flex-1">{f.name}</span>
              <span className="flex-shrink-0 text-slate-400">{formatBytes(f.size)}</span>
              <button
                onClick={() => removeFile(i)}
                aria-label={`Remove ${f.name}`}
                className="flex-shrink-0 w-4 h-4 rounded-full hover:bg-slate-200 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors"
              >
                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>

        {/* Add more files */}
        <label className="flex items-center gap-2 text-xs text-indigo-600 hover:text-indigo-800 cursor-pointer font-medium transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add more files
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            multiple
            className="sr-only"
            onChange={(e) => { if (e.target.files) addFiles(e.target.files); }}
          />
        </label>

        {validationError && <ValidationError message={validationError} />}

        <button
          onClick={() => onFiles(staged)}
          className="w-full bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-sm font-semibold py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 outline-none"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Analyze {staged.length} Document{staged.length !== 1 ? "s" : ""}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label
        className="block w-full cursor-pointer rounded-2xl transition-all duration-200"
        style={{
          background: dragging ? "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)" : "#ffffff",
          border: dragging ? "2px dashed #6366f1" : "2px dashed #cbd5e1",
          transform: dragging ? "scale(1.01)" : "scale(1)",
          boxShadow: dragging ? "0 8px 24px rgba(99,102,241,0.15)" : "0 1px 3px rgba(0,0,0,0.06)",
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        aria-label="Upload multiple documents"
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT_ATTR}
          multiple
          className="sr-only"
          onChange={(e) => { if (e.target.files) addFiles(e.target.files); }}
        />
        <DropZoneContent dragging={dragging} batch />
      </label>

      {validationError && <ValidationError message={validationError} />}
    </div>
  );
}

// ── Shared sub-components ────────────────────────────────────────────────────

function DropZoneContent({ dragging, batch = false }: { dragging: boolean; batch?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4 px-6 py-10 text-center">
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-200"
        style={{
          background: dragging ? "linear-gradient(135deg, #818cf8, #6366f1)" : "linear-gradient(135deg, #f1f5f9, #e2e8f0)",
          boxShadow: dragging ? "0 4px 12px rgba(99,102,241,0.3)" : "none",
        }}
      >
        <svg className="w-6 h-6 transition-colors duration-200" style={{ color: dragging ? "#ffffff" : "#94a3b8" }}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
      </div>
      {dragging ? (
        <p className="text-sm font-bold" style={{ color: "#4f46e5" }}>Drop to upload</p>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-semibold" style={{ color: "#334155" }}>
            Drag &amp; drop or{" "}
            <span style={{ color: "#4f46e5", textDecoration: "underline", textDecorationStyle: "dotted", textUnderlineOffset: 3 }}>
              browse {batch ? "files" : "a file"}
            </span>
          </p>
          <div className="flex items-center justify-center gap-1.5">
            {FORMAT_LABELS.map((fmt) => (
              <span key={fmt} className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                style={{ background: "#f1f5f9", color: "#94a3b8" }}>
                {fmt}
              </span>
            ))}
            <span className="text-[11px]" style={{ color: "#cbd5e1" }}>· max 20 MB each</span>
          </div>
        </div>
      )}
    </div>
  );
}

function ValidationError({ message }: { message: string }) {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-xl px-3 py-2.5 animate-fade-up"
      style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
      <svg className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: "#f87171" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span className="text-xs" style={{ color: "#b91c1c" }}>{message}</span>
    </div>
  );
}

// ── Public export ────────────────────────────────────────────────────────────

export type UploadZoneProps = SingleProps | BatchProps;

export function UploadZone(props: UploadZoneProps) {
  if (props.mode === "batch") {
    return <BatchUploadZone onFiles={props.onFiles} loading={props.loading} />;
  }
  return <SingleUploadZone onFile={props.onFile} loading={props.loading} warmingUp={props.warmingUp} />;
}
