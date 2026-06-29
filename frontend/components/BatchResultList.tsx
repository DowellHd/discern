"use client";
import type { BatchOut, Extraction } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";

interface Props {
  batch: BatchOut;
  onSelect: (extraction: Extraction) => void;
}

function confVariant(pct: number): BadgeVariant {
  if (pct >= 75) return "success";
  if (pct >= 45) return "warn";
  return "danger";
}

export function BatchResultList({ batch, onSelect }: Props) {
  const { results, errors } = batch;
  const total = results.length + errors.length;

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="px-1 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold tracking-tight" style={{ color: "#0f172a" }}>
            Batch Results
          </h2>
          <p className="text-sm mt-0.5" style={{ color: "#64748b" }}>
            {results.length} of {total} extracted successfully
            {errors.length > 0 && ` · ${errors.length} error${errors.length !== 1 ? "s" : ""}`}
          </p>
        </div>
      </div>

      {results.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-200">
            <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
              Extracted Documents
            </h3>
          </div>
          <ul className="divide-y divide-slate-100">
            {results.map((ext) => {
              const label = ext.doc_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              const confPct = Math.round(ext.doc_type_confidence * 100);
              return (
                <li key={ext.id}>
                  <button
                    onClick={() => onSelect(ext)}
                    className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-slate-50 transition-colors group"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-800 truncate group-hover:text-indigo-700 transition-colors">
                        {label}
                      </p>
                      <p className="text-xs text-slate-400 truncate mt-0.5">
                        {ext.fields.length} field{ext.fields.length !== 1 ? "s" : ""} · {new Date(ext.created_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                    <Badge variant={confVariant(confPct)}>{confPct}%</Badge>
                    <svg className="w-4 h-4 text-slate-300 group-hover:text-indigo-400 flex-shrink-0 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {errors.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3 bg-red-50 border-b border-red-100">
            <h3 className="text-[11px] font-bold text-red-500 uppercase tracking-widest">
              Errors
            </h3>
          </div>
          <ul className="divide-y divide-slate-100">
            {errors.map((msg, i) => (
              <li key={i} className="px-5 py-3.5 flex items-start gap-2.5">
                <svg className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs text-slate-600 leading-relaxed">{msg}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
