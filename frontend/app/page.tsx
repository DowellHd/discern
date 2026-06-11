"use client";
import { useState, useCallback } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ExtractionResult } from "@/components/ExtractionResult";
import { SearchPanel } from "@/components/SearchPanel";
import { extractDocument } from "@/lib/api";
import type { Extraction } from "@/lib/types";

export default function Home() {
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"upload" | "search">("upload");

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
      {/* Header */}
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center gap-4 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white font-bold text-sm">D</div>
          <span className="text-lg font-bold tracking-tight">Discern</span>
        </div>
        <span className="text-slate-400 text-sm">Document Intelligence</span>
        <div className="ml-auto flex gap-1">
          {(["upload", "search"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                ${tab === t ? "bg-indigo-600 text-white" : "text-slate-300 hover:text-white hover:bg-slate-700"}`}
            >
              {t === "upload" ? "Extract" : "Search"}
            </button>
          ))}
        </div>
      </header>

      {/* Body */}
      <main className="flex flex-1 max-w-6xl mx-auto w-full px-6 py-8 gap-8">
        {/* Left panel */}
        <aside className="w-full max-w-sm flex flex-col gap-6">
          {tab === "upload" ? (
            <>
              <div>
                <h1 className="text-xl font-bold text-slate-800 mb-1">Upload Document</h1>
                <p className="text-sm text-slate-500">Upload a photo or scan of a connection card or prayer request.</p>
              </div>
              <UploadZone onFile={handleFile} loading={loading} />
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              {!extraction && !loading && (
                <div className="text-center text-sm text-slate-400 py-6">
                  Upload an image to extract structured data
                </div>
              )}
            </>
          ) : (
            <>
              <div>
                <h1 className="text-xl font-bold text-slate-800 mb-1">Search Records</h1>
                <p className="text-sm text-slate-500">Search across all extracted documents.</p>
              </div>
              <SearchPanel onSelect={setExtraction} />
            </>
          )}
        </aside>

        {/* Right panel — result */}
        <section className="flex-1 min-w-0">
          {extraction ? (
            <ExtractionResult extraction={extraction} />
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400">
              <div className="text-center space-y-2">
                <div className="text-5xl">📄</div>
                <p className="text-sm">Extracted fields will appear here</p>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
