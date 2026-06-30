"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Extraction, Template } from "@/lib/types";
import { searchDocuments, getReviewQueue } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import type { BadgeVariant } from "@/components/ui/Badge";

interface Props {
  templates: Template[];
  onSelect: (extraction: Extraction) => void;
}

type Mode = "all" | "review";

const CATEGORY_LABELS: Record<string, string> = {
  church: "Church",
  personal: "Personal",
  business: "Business",
};

const STATUS_LABELS: Record<string, string> = {
  "": "Any status",
  pending: "Pending",
  contacted: "Contacted",
  done: "Done",
};

function confVariant(pct: number): BadgeVariant {
  if (pct >= 75) return "success";
  if (pct >= 45) return "warn";
  return "danger";
}

const PAGE_SIZE = 20;

export function LibraryPanel({ templates, onSelect }: Props) {
  const [mode, setMode] = useState<Mode>("all");
  const [q, setQ] = useState("");
  const [docType, setDocType] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [results, setResults] = useState<Extraction[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const categories = Array.from(new Set(templates.map((t) => t.category))).sort();

  const visibleTemplates = category
    ? templates.filter((t) => t.category === category)
    : templates;

  const doSearch = useCallback(
    async (reset: boolean) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const nextOffset = reset ? 0 : offset;
      reset ? setLoading(true) : setLoadingMore(true);
      setError(null);

      try {
        let resp;
        if (mode === "review") {
          resp = await getReviewQueue(0.7, PAGE_SIZE, nextOffset);
        } else {
          resp = await searchDocuments(
            q || undefined,
            docType || undefined,
            status || undefined,
            PAGE_SIZE,
            nextOffset,
          );
        }
        if (reset) {
          setResults(resp.results);
          setOffset(PAGE_SIZE);
        } else {
          setResults((prev) => [...prev, ...resp.results]);
          setOffset(nextOffset + PAGE_SIZE);
        }
        setTotal(resp.total);
      } catch (err: unknown) {
        if ((err as Error)?.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load documents");
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [mode, q, docType, status, offset],
  );

  // Reload when filters change
  useEffect(() => {
    doSearch(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, docType, status]);

  // Clear type filter when category changes (type may no longer be valid)
  useEffect(() => {
    if (category && docType) {
      const match = templates.find((t) => t.key === docType);
      if (match && match.category !== category) setDocType("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    doSearch(true);
  }

  const hasMore = results.length < total;

  return (
    <div className="space-y-3">
      {/* ── Mode toggle ─────────────────────────────────── */}
      <div
        className="flex items-center gap-1 self-start rounded-lg p-1"
        style={{ background: "#f1f5f9" }}
        role="group"
        aria-label="Library view"
      >
        {(["all", "review"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => { setMode(m); setOffset(0); }}
            aria-pressed={mode === m}
            className="transition-all outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            style={{
              padding: "4px 12px",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              background: mode === m ? "#ffffff" : "transparent",
              color: mode === m ? "#334155" : "#94a3b8",
              boxShadow: mode === m ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            {m === "all" ? "All Documents" : "Needs Review"}
          </button>
        ))}
      </div>

      {/* ── Search + filters ────────────────────────────── */}
      {mode === "all" && (
        <form onSubmit={handleSearch} className="space-y-2" role="search">
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="search"
              placeholder="Search fields…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Search query"
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent placeholder:text-slate-400"
            />
          </div>

          {/* Category pills */}
          {categories.length > 0 && (
            <div className="flex gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => { setCategory(""); setDocType(""); }}
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors"
                style={!category
                  ? { background: "#e0e7ff", color: "#4338ca", borderColor: "#c7d2fe" }
                  : { background: "#f8fafc", color: "#94a3b8", borderColor: "#e2e8f0" }
                }
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setCategory(cat === category ? "" : cat)}
                  className="text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors"
                  style={category === cat
                    ? { background: "#e0e7ff", color: "#4338ca", borderColor: "#c7d2fe" }
                    : { background: "#f8fafc", color: "#94a3b8", borderColor: "#e2e8f0" }
                  }
                >
                  {CATEGORY_LABELS[cat] ?? cat}
                </button>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              aria-label="Filter by document type"
              className="flex-1 min-w-0 border border-slate-300 rounded-xl px-3 py-2 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 text-slate-700"
            >
              <option value="">All types</option>
              {visibleTemplates.map((t) => (
                <option key={t.key} value={t.key}>{t.label}</option>
              ))}
            </select>

            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              aria-label="Filter by status"
              className="flex-1 min-w-0 border border-slate-300 rounded-xl px-3 py-2 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 text-slate-700"
            >
              {Object.entries(STATUS_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>

            <button
              type="submit"
              disabled={loading}
              className="flex-shrink-0 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white px-3 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5 outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              {loading ? <Spinner size="sm" className="text-white" /> : "Search"}
            </button>
          </div>
        </form>
      )}

      {/* ── Error ───────────────────────────────────────── */}
      {error && (
        <div role="alert" className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2.5">
          <svg className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-xs text-red-700">{error}</span>
        </div>
      )}

      {/* ── Count ───────────────────────────────────────── */}
      {!loading && !error && (
        <p className="text-xs font-semibold text-slate-400" aria-live="polite">
          {total === 0
            ? (mode === "review" ? "No documents need review" : "No documents yet")
            : `${total} document${total !== 1 ? "s" : ""}${mode === "review" ? " need review" : ""}`}
        </p>
      )}

      {/* ── Loading skeleton ────────────────────────────── */}
      {loading && (
        <div className="space-y-2" aria-label="Loading" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card p-3.5 flex flex-col gap-2" aria-hidden="true">
              <div className="skeleton h-3.5 w-32" />
              <div className="skeleton h-2.5 w-48" />
            </div>
          ))}
        </div>
      )}

      {/* ── Result list ─────────────────────────────────── */}
      {!loading && results.length > 0 && (
        <ul className="space-y-2" role="list" aria-label="Documents">
          {results.map((r) => {
            const label = r.doc_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
            const confPct = Math.round(r.doc_type_confidence * 100);
            const dateStr = new Date(r.created_at).toLocaleDateString(undefined, {
              month: "short", day: "numeric", year: "numeric",
            });
            const previewField = r.fields.find((f) => f.value && !f.sensitive);

            return (
              <li key={r.id}>
                <button
                  onClick={() => onSelect(r)}
                  className="w-full text-left card px-4 py-3.5 hover:border-indigo-200 hover:shadow-md transition-all duration-150 focus-visible:ring-2 focus-visible:ring-indigo-400 outline-none group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-800 group-hover:text-indigo-700 transition-colors truncate">
                      {previewField?.value ?? label}
                    </p>
                    <Badge variant={confVariant(confPct)} className="flex-shrink-0 tabular-nums">
                      {confPct}%
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium mt-0.5">
                    {label} · {dateStr}
                    {r.follow_up_status && (
                      <span className="ml-1.5 text-amber-500 font-semibold capitalize">· {r.follow_up_status}</span>
                    )}
                  </p>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {/* ── Load more ───────────────────────────────────── */}
      {!loading && hasMore && (
        <button
          onClick={() => doSearch(false)}
          disabled={loadingMore}
          className="w-full text-xs font-semibold text-slate-500 hover:text-slate-700 py-2.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          {loadingMore ? <Spinner size="sm" className="text-slate-400" /> : null}
          {loadingMore ? "Loading…" : `Load more (${total - results.length} remaining)`}
        </button>
      )}

      {/* ── Empty state ──────────────────────────────────── */}
      {!loading && results.length === 0 && !error && (
        <div className="text-center py-8 space-y-3">
          <div className="mx-auto w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-600">
              {mode === "review" ? "Queue is clear" : "No documents found"}
            </p>
            <p className="text-xs text-slate-400">
              {mode === "review"
                ? "All extractions are above the confidence threshold"
                : "Try adjusting your filters or upload a document"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
