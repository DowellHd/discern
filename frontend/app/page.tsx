"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ExtractionResult } from "@/components/ExtractionResult";
import { BatchResultList } from "@/components/BatchResultList";
import { LibraryPanel } from "@/components/LibraryPanel";
import { StatsPanel } from "@/components/StatsPanel";
import { AuthModal } from "@/components/AuthModal";
import Image from "next/image";
import { extractDocument, getTemplates, getToken, clearToken } from "@/lib/api";
import type { BatchOut, Extraction, Template } from "@/lib/types";

interface BatchProgress {
  total: number;
  done: number;
  current: string | null;
  results: Extraction[];
  errors: string[];
}

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const WARM_UP_DELAY_MS = 10_000;

type Tab = "upload" | "library" | "stats";

const TABS: { id: Tab; label: string }[] = [
  { id: "upload",  label: "Extract" },
  { id: "library", label: "Library" },
  { id: "stats",   label: "Stats" },
];

const CATEGORY_LABELS: Record<string, string> = {
  church: "Church",
  personal: "Personal",
  business: "Business",
};

export default function Home() {
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [batchResult, setBatchResult] = useState<BatchOut | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [singleStagedFile, setSingleStagedFile] = useState<File | null>(null);
  const [batchStagedFiles, setBatchStagedFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [warmingUp, setWarmingUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("upload");
  const [docType, setDocType] = useState("");
  const [templates, setTemplates] = useState<Template[]>([]);
  const [batchMode, setBatchMode] = useState(false);
  const [librarySelection, setLibrarySelection] = useState<Extraction | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [showAuth, setShowAuth] = useState(false);
  const warmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auth gate: show modal when not in demo mode and no token stored
  useEffect(() => {
    if (!DEMO_MODE && !getToken()) setShowAuth(true);
  }, []);

  useEffect(() => {
    getTemplates()
      .then((r) => setTemplates(r.templates))
      .catch(() => {/* API may be cold; fallback to empty (auto-detect only) */});
  }, []);

  useEffect(() => {
    if (loading) {
      setWarmingUp(false);
      warmTimer.current = setTimeout(() => setWarmingUp(true), WARM_UP_DELAY_MS);
    } else {
      if (warmTimer.current) clearTimeout(warmTimer.current);
      setWarmingUp(false);
    }
    return () => { if (warmTimer.current) clearTimeout(warmTimer.current); };
  }, [loading]);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setBatchResult(null);
    setLoading(true);
    try {
      const result = await extractDocument(file, docType || undefined);
      setExtraction(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }, [docType]);

  const handleFiles = useCallback(async (files: File[]) => {
    setError(null);
    setExtraction(null);
    setBatchResult(null);
    const progress: BatchProgress = { total: files.length, done: 0, current: null, results: [], errors: [] };
    setBatchProgress({ ...progress });
    setLoading(true);
    for (const file of files) {
      progress.current = file.name;
      setBatchProgress({ ...progress });
      try {
        const result = await extractDocument(file, docType || undefined);
        progress.results = [...progress.results, result];
      } catch (err: unknown) {
        progress.errors = [...progress.errors, `${file.name}: ${err instanceof Error ? err.message : "Failed"}`];
      }
      progress.done += 1;
      setBatchProgress({ ...progress });
    }
    setBatchResult({ results: progress.results, errors: progress.errors });
    setBatchProgress(null);
    setLoading(false);
  }, [docType]);

  function toggleBatchMode(next: boolean) {
    setBatchMode(next);
    setExtraction(null);
    setBatchResult(null);
    setBatchProgress(null);
    setError(null);
  }

  const rightPanel = (() => {
    if (tab === "library") {
      return librarySelection
        ? <ExtractionResult extraction={librarySelection} onUpdate={setLibrarySelection} />
        : <EmptyResultState />;
    }
    if (batchProgress) {
      const pct = batchProgress.total > 0 ? Math.round((batchProgress.done / batchProgress.total) * 100) : 0;
      return (
        <div className="card p-6 space-y-5 animate-fade-up">
          <div>
            <h2 className="text-base font-bold text-slate-800">Processing batch</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {batchProgress.done} of {batchProgress.total} complete
              {batchProgress.current && ` · ${batchProgress.current}`}
            </p>
          </div>
          <div className="space-y-1">
            <div className="progress-track h-2 rounded-full" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
              <div className="progress-thumb rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
            </div>
            <p className="text-xs text-slate-400 text-right">{pct}%</p>
          </div>
          {batchProgress.results.length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-2">Completed</p>
              <ul className="space-y-1.5">
                {batchProgress.results.map((e) => (
                  <li key={e.id} className="flex items-center gap-2 text-xs text-slate-700 bg-green-50 rounded-lg px-3 py-2">
                    <svg className="w-3.5 h-3.5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                    <span className="truncate font-medium">{e.doc_type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
                    <span className="ml-auto text-slate-400">{Math.round(e.doc_type_confidence * 100)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {batchProgress.errors.length > 0 && (
            <ul className="space-y-1">
              {batchProgress.errors.map((msg, i) => (
                <li key={i} className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 truncate">{msg}</li>
              ))}
            </ul>
          )}
        </div>
      );
    }
    if (batchResult && extraction) {
      return (
        <div className="space-y-3">
          <button
            onClick={() => setExtraction(null)}
            className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
            Back to batch results
          </button>
          <ExtractionResult extraction={extraction} onUpdate={setExtraction} />
        </div>
      );
    }
    if (batchResult) {
      return (
        <BatchResultList
          batch={batchResult}
          onSelect={(e) => setExtraction(e)}
        />
      );
    }
    if (extraction) {
      return <ExtractionResult extraction={extraction} onUpdate={setExtraction} />;
    }
    return <EmptyResultState />;
  })();


  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-20 flex items-center px-4 sm:px-6 gap-4"
        style={{ height: 56, background: "#0f172a", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <a
          href="/"
          className="flex items-center gap-2.5 flex-shrink-0 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Image
            src="/icon.png"
            alt="Discern"
            width={32}
            height={32}
            className="w-8 h-8 rounded-xl shadow-lg flex-shrink-0"
            priority
          />
          <div className="flex items-baseline gap-2">
            <span className="font-bold text-[15px] tracking-tight" style={{ color: "#f1f5f9" }}>Discern</span>
            <span className="hidden sm:block text-xs font-medium" style={{ color: "#475569" }}>Document Intelligence</span>
          </div>
        </a>

        <nav
          className="ml-auto flex items-center gap-1"
          aria-label="Main navigation"
          style={{ background: "rgba(255,255,255,0.07)", borderRadius: 12, padding: 4 }}
        >
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              aria-current={tab === id ? "page" : undefined}
              className="outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 transition-all duration-150"
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                background: tab === id ? "#ffffff" : "transparent",
                color: tab === id ? "#0f172a" : "#94a3b8",
                boxShadow: tab === id ? "0 1px 3px rgba(0,0,0,0.15)" : "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              {label}
            </button>
          ))}
        </nav>

        {/* Auth controls (hidden in demo mode) */}
        {!DEMO_MODE && (
          <div className="ml-3 flex items-center gap-2 flex-shrink-0">
            {userEmail ? (
              <>
                <span className="text-xs text-slate-400 hidden sm:block">{userEmail}</span>
                <button
                  onClick={() => { clearToken(); setUserEmail(null); setShowAuth(true); }}
                  className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : (
              <button
                onClick={() => setShowAuth(true)}
                className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Sign in
              </button>
            )}
          </div>
        )}
      </header>

      {showAuth && !DEMO_MODE && (
        <AuthModal onAuth={(email) => { setUserEmail(email); setShowAuth(false); }} />
      )}

      {/* ── Body ──────────────────────────────────────────── */}
      {tab === "stats" ? (
        <main className="flex-1 w-full max-w-4xl mx-auto px-4 sm:px-6 py-8" role="main">
          <div className="px-1 mb-5">
            <h1 className="text-lg font-bold tracking-tight" style={{ color: "#0f172a" }}>Stats &amp; Export</h1>
            <p className="text-sm mt-0.5 leading-relaxed" style={{ color: "#64748b" }}>
              Aggregate metrics and CSV export for all extracted records.
            </p>
          </div>
          <StatsPanel />
        </main>
      ) : (
        <main
          className="flex flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 gap-6 flex-col sm:flex-row"
          role="main"
        >
          {/* Left panel */}
          <aside className="w-full sm:w-80 lg:w-88 flex-shrink-0 flex flex-col gap-4" aria-label="Controls">
            {tab === "upload" ? (
              <>
                <div className="px-1 flex items-start justify-between gap-2">
                  <div>
                    <h1 className="text-lg font-bold tracking-tight" style={{ color: "#0f172a" }}>Upload Document</h1>
                    <p className="text-sm mt-0.5 leading-relaxed" style={{ color: "#64748b" }}>
                      Photo, scan, or PDF — receipts, business cards, forms, church records, and more.
                    </p>
                  </div>
                </div>

                {/* Single / Batch toggle */}
                <div
                  className="flex items-center gap-1 self-start rounded-lg p-1"
                  style={{ background: "#f1f5f9" }}
                  role="group"
                  aria-label="Upload mode"
                >
                  {([false, true] as const).map((isBatch) => (
                    <button
                      key={String(isBatch)}
                      onClick={() => toggleBatchMode(isBatch)}
                      aria-pressed={batchMode === isBatch}
                      className="transition-all outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
                      style={{
                        padding: "4px 12px",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 600,
                        background: batchMode === isBatch ? "#ffffff" : "transparent",
                        color: batchMode === isBatch ? "#334155" : "#94a3b8",
                        boxShadow: batchMode === isBatch ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      {isBatch ? "Batch" : "Single"}
                    </button>
                  ))}
                </div>

                {/* Document type selector — single mode only */}
                {!batchMode && (
                  <div>
                    <label
                      htmlFor="doc-type-select"
                      className="block text-xs font-semibold mb-1.5"
                      style={{ color: "#64748b" }}
                    >
                      Document type
                    </label>
                    <select
                      id="doc-type-select"
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                      className="w-full rounded-xl px-3 py-2 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
                      style={{
                        background: "#fff",
                        border: "1.5px solid #e2e8f0",
                        color: "#334155",
                        cursor: "pointer",
                      }}
                    >
                      <option value="">Auto-detect</option>
                      {templates.length > 0 ? (
                        Object.entries(
                          templates.reduce<Record<string, Template[]>>((acc, t) => {
                            (acc[t.category] ??= []).push(t);
                            return acc;
                          }, {})
                        ).map(([cat, group]) => (
                          <optgroup key={cat} label={CATEGORY_LABELS[cat] ?? cat}>
                            {group.map((t) => (
                              <option key={t.key} value={t.key}>{t.label}</option>
                            ))}
                          </optgroup>
                        ))
                      ) : null}
                    </select>
                    {!docType && (
                      <p className="text-xs mt-1" style={{ color: "#94a3b8" }}>
                        Auto-detect will identify the document type for you.
                      </p>
                    )}
                  </div>
                )}

                {batchMode ? (
                  <UploadZone
                    key="batch"
                    mode="batch"
                    onFiles={handleFiles}
                    onFilesChange={setBatchStagedFiles}
                    loading={loading}
                    initialFiles={batchStagedFiles.length > 0 ? batchStagedFiles : singleStagedFile ? [singleStagedFile] : []}
                  />
                ) : (
                  <UploadZone
                    key={extraction?.id ?? "single"}
                    mode="single"
                    onFile={handleFile}
                    onStage={setSingleStagedFile}
                    loading={loading}
                    warmingUp={warmingUp}
                  />
                )}

                {error && (
                  <div
                    role="alert"
                    className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-2xl px-4 py-3.5 animate-fade-up"
                  >
                    <svg className="w-4 h-4 mt-0.5 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <p className="text-sm font-semibold text-red-800">
                        {batchMode ? "Batch upload failed" : "Extraction failed"}
                      </p>
                      <p className="text-xs text-red-600 mt-0.5 leading-relaxed">{error}</p>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="px-1">
                  <h1 className="text-lg font-bold tracking-tight" style={{ color: "#0f172a" }}>Library</h1>
                  <p className="text-sm mt-0.5 leading-relaxed" style={{ color: "#64748b" }}>
                    Browse, search, and review all extracted documents.
                  </p>
                </div>
                <LibraryPanel
                  templates={templates}
                  onSelect={setLibrarySelection}
                />
              </>
            )}
          </aside>

          {/* Right panel */}
          <section className="flex-1 min-w-0" aria-label="Extraction result">
            {rightPanel}
          </section>
        </main>
      )}
    </div>
  );
}

function EmptyResultState() {
  return (
    <div
      className="h-full min-h-72 flex items-center justify-center rounded-2xl animate-fade-up"
      style={{ background: "rgba(255,255,255,0.5)", border: "1.5px dashed #e2e8f0" }}
    >
      <div className="text-center space-y-5 py-12 px-8">
        <div className="relative mx-auto w-20 h-20">
          <div className="absolute inset-0 rounded-2xl rotate-6" style={{ background: "#e0e7ff", border: "1px solid #c7d2fe" }} />
          <div className="absolute inset-0 rounded-2xl rotate-2" style={{ background: "#eef2ff", border: "1px solid #c7d2fe" }} />
          <div className="absolute inset-0 rounded-2xl flex items-center justify-center" style={{ background: "#ffffff", border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}>
            <svg className="w-9 h-9" style={{ color: "#a5b4fc" }} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>
        <div className="space-y-1.5">
          <p className="text-base font-bold" style={{ color: "#334155" }}>No document extracted yet</p>
          <p className="text-sm" style={{ color: "#94a3b8" }}>
            Upload any document — receipt, business card,<br />form, or church record — to see structured fields here
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-1">
          {["Upload", "Extract", "Search"].map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
                  style={{ background: "#e0e7ff", color: "#6366f1" }}>
                  {i + 1}
                </div>
                <span className="text-[11px] font-semibold" style={{ color: "#94a3b8" }}>{step}</span>
              </div>
              {i < 2 && <div className="w-4 h-px" style={{ background: "#e2e8f0" }} />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
