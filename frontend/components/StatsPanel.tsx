"use client";
import { useEffect, useState } from "react";
import { getStats, exportCsvUrl } from "@/lib/api";
import type { Stats } from "@/lib/types";
import { Spinner } from "@/components/ui/Spinner";

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="card px-5 py-4 space-y-1">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">{label}</p>
      <p className="text-2xl font-bold tracking-tight" style={{ color: accent ?? "#0f172a" }}>
        {value}
      </p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

export function StatsPanel() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load stats"));
  }, []);

  if (error) {
    return (
      <div role="alert" className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-2xl px-4 py-3.5">
        <svg className="w-4 h-4 mt-0.5 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-sm text-red-700">{error}</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner size="lg" className="text-indigo-400" />
      </div>
    );
  }

  const avgPct = Math.round(stats.avg_confidence * 100);
  const docTypes = Object.entries(stats.by_doc_type).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-5 animate-fade-up">
      {/* ── Summary cards ────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total records" value={stats.total_documents} />
        <StatCard
          label="Avg confidence"
          value={`${avgPct}%`}
          accent={avgPct >= 75 ? "#10b981" : avgPct >= 45 ? "#f59e0b" : "#ef4444"}
        />
        <StatCard
          label="Review queue"
          value={stats.review_queue}
          sub="below 70% confidence"
          accent={stats.review_queue > 0 ? "#f59e0b" : "#10b981"}
        />
        <StatCard label="Doc types" value={docTypes.length} />
      </div>

      {/* ── By document type ─────────────────────────────── */}
      {docTypes.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-200">
            <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
              Records by type
            </h3>
          </div>
          <div className="divide-y divide-slate-100">
            {docTypes.map(([type, count]) => {
              const pct = stats.total_documents > 0 ? (count / stats.total_documents) * 100 : 0;
              const label = type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              return (
                <div key={type} className="px-5 py-3.5 flex items-center gap-4">
                  <span className="text-sm font-medium text-slate-700 w-40 flex-shrink-0 truncate">{label}</span>
                  <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-indigo-400 transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold text-slate-600 tabular-nums w-8 text-right flex-shrink-0">
                    {count}
                  </span>
                  <a
                    href={exportCsvUrl(type)}
                    download
                    className="text-[11px] font-semibold text-indigo-500 hover:text-indigo-700 flex-shrink-0 transition-colors"
                    aria-label={`Export ${label} as CSV`}
                  >
                    Export
                  </a>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Export all ───────────────────────────────────── */}
      <div className="flex justify-end">
        <a
          href={exportCsvUrl()}
          download
          className="flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl border bg-white hover:bg-slate-50 text-slate-700 border-slate-200 hover:border-slate-300 transition-colors shadow-sm"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export all records as CSV
        </a>
      </div>
    </div>
  );
}
