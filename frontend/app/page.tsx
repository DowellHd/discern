"use client";
import { useState, useCallback, useEffect, useRef } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ExtractionResult } from "@/components/ExtractionResult";
import { SearchPanel } from "@/components/SearchPanel";
import { extractDocument } from "@/lib/api";
import type { Extraction } from "@/lib/types";

const WARM_UP_DELAY_MS = 10_000;

export default function Home() {
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [loading, setLoading] = useState(false);
  const [warmingUp, setWarmingUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"upload" | "search">("upload");
  const warmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    setLoading(true);
    try {
      const result = await extractDocument(file);
      setExtraction(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 h-14 bg-slate-900 border-b border-white/5 flex items-center px-4 sm:px-6 gap-4">
        {/* Brand mark */}
        <a href="/" className="flex items-center gap-2.5 flex-shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 rounded-lg">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 select-none"
            style={{ background: "linear-gradient(135deg, #6366f1 0%, #4338ca 100%)" }}
            aria-hidden="true"
          >
            <span className="text-white font-bold text-sm tracking-tight">D</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-white font-bold text-[15px] tracking-tight">Discern</span>
            <span className="hidden sm:block text-slate-500 text-xs font-medium">Document Intelligence</span>
          </div>
        </a>

        {/* Nav */}
        <nav
          className="ml-auto flex items-center gap-0.5 bg-slate-800/70 rounded-xl p-1"
          aria-label="Main navigation"
        >
          {(["upload", "search"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              aria-current={tab === t ? "page" : undefined}
              className={`
                px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 outline-none
                focus-visible:ring-2 focus-visible:ring-indigo-400
                ${tab === t
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
                }
              `}
            >
              {t === "upload" ? "Extract" : "Search"}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Body ──────────────────────────────────────────── */}
      <main
        className="flex flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 gap-8 flex-col sm:flex-row"
        role="main"
      >
        {/* Left panel */}
        <aside
          className="w-full sm:w-80 lg:w-96 flex-shrink-0 flex flex-col gap-5"
          aria-label="Controls"
        >
          {tab === "upload" ? (
            <>
              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Upload Document</h1>
                <p className="text-sm text-slate-500 mt-1 leading-relaxed">
                  Upload a photo or scan of a connection card or prayer request.
                </p>
              </div>

              <UploadZone
                key={extraction?.id ?? "empty"}
                onFile={handleFile}
                loading={loading}
                warmingUp={warmingUp}
              />

              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-2xl px-4 py-3.5 animate-fade-up"
                >
                  <svg className="w-4 h-4 mt-0.5 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className="text-sm font-semibold text-red-800">Extraction failed</p>
                    <p className="text-xs text-red-600 mt-0.5 leading-relaxed">{error}</p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Search Records</h1>
                <p className="text-sm text-slate-500 mt-1 leading-relaxed">
                  Search across all extracted documents.
                </p>
              </div>
              <SearchPanel
                onSelect={(e) => {
                  setExtraction(e);
                  setTab("upload");
                }}
              />
            </>
          )}
        </aside>

        {/* Right panel — result */}
        <section className="flex-1 min-w-0" aria-label="Extraction result">
          {extraction ? (
            <ExtractionResult extraction={extraction} />
          ) : (
            <EmptyResultState />
          )}
        </section>
      </main>
    </div>
  );
}

function EmptyResultState() {
  return (
    <div className="h-full min-h-72 flex items-center justify-center">
      <div className="text-center space-y-4 animate-fade-up">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center">
          <svg className="w-8 h-8 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-500">No document extracted yet</p>
          <p className="text-xs text-slate-400">Upload an image to see extracted fields here</p>
        </div>
      </div>
    </div>
  );
}
