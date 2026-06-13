"use client";
import { useState } from "react";
import type { Extraction } from "@/lib/types";
import { searchDocuments } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";

interface Props {
  onSelect: (extraction: Extraction) => void;
}

function confVariant(pct: number): BadgeVariant {
  if (pct >= 75) return "success";
  if (pct >= 45) return "warn";
  return "danger";
}

export function SearchPanel({ onSelect }: Props) {
  const [q, setQ] = useState("");
  const [docType, setDocType] = useState("");
  const [results, setResults] = useState<Extraction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await searchDocuments(q || undefined, docType || undefined, 20, 0);
      setResults(resp.results);
      setTotal(resp.total);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* ── Search form ─────────────────────────────────── */}
      <form onSubmit={handleSearch} className="space-y-2.5" role="search">
        {/* Query input */}
        <div className="relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true">
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="search"
            placeholder="Search extracted fields…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search query"
            className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent placeholder:text-slate-400 transition-shadow"
          />
        </div>

        {/* Filters + submit */}
        <div className="flex gap-2">
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            aria-label="Filter by document type"
            className="flex-1 min-w-0 border border-slate-300 rounded-xl px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent text-slate-700 transition-shadow"
          >
            <option value="">All types</option>
            <option value="connection_card">Connection Card</option>
            <option value="prayer_request">Prayer Request</option>
          </select>

          <button
            type="submit"
            disabled={loading}
            className="flex-shrink-0 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 disabled:opacity-60 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors flex items-center gap-2 min-w-[80px] justify-center focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 outline-none"
          >
            {loading ? <Spinner size="sm" className="text-white" /> : "Search"}
          </button>
        </div>
      </form>

      {/* ── Error ───────────────────────────────────────── */}
      {error && (
        <div role="alert" className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2.5 animate-fade-up">
          <svg className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs text-red-700">{error}</span>
        </div>
      )}

      {/* ── Results count ────────────────────────────────── */}
      {searched && !loading && !error && (
        <p className="text-xs font-semibold text-slate-500" aria-live="polite">
          {total === 0 ? "No results" : `${total} result${total !== 1 ? "s" : ""}`}
        </p>
      )}

      {/* ── Skeleton loading ─────────────────────────────── */}
      {loading && (
        <div className="space-y-2" aria-label="Loading results" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card p-3.5 flex flex-col gap-2.5" aria-hidden="true">
              <div className="skeleton h-3.5 w-32" />
              <div className="skeleton h-2.5 w-48" />
            </div>
          ))}
        </div>
      )}

      {/* ── Result cards ─────────────────────────────────── */}
      {!loading && results.length > 0 && (
        <ul className="space-y-2" role="list" aria-label="Search results">
          {results.map((r) => {
            const docLabel = r.doc_type
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase());
            const confPct = Math.round(r.doc_type_confidence * 100);
            const dateStr = new Date(r.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <li key={r.id}>
                <button
                  onClick={() => onSelect(r)}
                  className="w-full text-left card px-4 py-3.5 hover:border-indigo-200 hover:shadow-md transition-all duration-150 focus-visible:ring-2 focus-visible:ring-indigo-400 outline-none group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-800 group-hover:text-indigo-700 transition-colors">
                      {docLabel}
                    </p>
                    <Badge variant={confVariant(confPct)} className="flex-shrink-0 mt-0.5 tabular-nums">
                      {confPct}%
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium mt-1">{dateStr}</p>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {/* ── Empty state (after search) ───────────────────── */}
      {searched && !loading && results.length === 0 && !error && (
        <div className="text-center py-8 space-y-3 animate-fade-up">
          <div className="mx-auto w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-600">No records found</p>
            <p className="text-xs text-slate-400">Try different search terms or document type</p>
          </div>
        </div>
      )}

      {/* ── Pre-search hint ──────────────────────────────── */}
      {!searched && !loading && (
        <p className="text-xs text-slate-400 text-center py-4">
          Enter a term above to search extracted records
        </p>
      )}
    </div>
  );
}
