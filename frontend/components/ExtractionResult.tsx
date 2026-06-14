"use client";
import { useState } from "react";
import type { Extraction, Field, FollowUpStatus } from "@/lib/types";
import { FieldRow } from "./FieldRow";
import { overlayUrl, patchField, patchStatus, exportCsvUrl } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";

interface Props {
  extraction: Extraction;
  onUpdate?: (updated: Extraction) => void;
}

function confVariant(pct: number): BadgeVariant {
  if (pct >= 75) return "success";
  if (pct >= 45) return "warn";
  return "danger";
}

const STATUS_OPTIONS: { value: FollowUpStatus; label: string; color: string }[] = [
  { value: null,        label: "No follow-up",  color: "#94a3b8" },
  { value: "pending",   label: "Pending",        color: "#f59e0b" },
  { value: "contacted", label: "Contacted",      color: "#6366f1" },
  { value: "done",      label: "Done",           color: "#10b981" },
];

function statusVariant(s: FollowUpStatus): BadgeVariant {
  if (s === "done")      return "success";
  if (s === "contacted") return "neutral";
  if (s === "pending")   return "warn";
  return "neutral";
}

export function ExtractionResult({ extraction, onUpdate }: Props) {
  const [fields, setFields] = useState<Field[]>(extraction.fields);
  const [status, setStatus] = useState<FollowUpStatus>(extraction.follow_up_status);
  const [showOverlay, setShowOverlay] = useState(true);
  const [copied, setCopied] = useState(false);
  const [savingField, setSavingField] = useState<string | null>(null);
  const [savingStatus, setSavingStatus] = useState(false);

  async function handleChange(name: string, value: string) {
    setFields((prev) => prev.map((f) => (f.name === name ? { ...f, value } : f)));
    setSavingField(name);
    try {
      const updated = await patchField(extraction.id, name, value || null);
      setFields(updated.fields);
      onUpdate?.(updated);
    } catch {
      // revert on error
      setFields((prev) => prev.map((f) => (f.name === name ? { ...f, value: extraction.fields.find(o => o.name === name)?.value ?? null } : f)));
    } finally {
      setSavingField(null);
    }
  }

  async function handleStatus(next: FollowUpStatus) {
    setStatus(next);
    setSavingStatus(true);
    try {
      const updated = await patchStatus(extraction.id, next);
      setStatus(updated.follow_up_status);
      onUpdate?.(updated);
    } catch {
      setStatus(extraction.follow_up_status);
    } finally {
      setSavingStatus(false);
    }
  }

  async function copyJSON() {
    const payload = fields.map(({ name, value, confidence, capture }) => ({
      field: name,
      value,
      confidence: Math.round(confidence * 100) / 100,
      capture,
    }));
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  }

  const docLabel = extraction.doc_type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  const confPct = Math.round(extraction.doc_type_confidence * 100);
  const createdAt = new Date(extraction.created_at).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const currentStatus = STATUS_OPTIONS.find((o) => o.value === status) ?? STATUS_OPTIONS[0];

  return (
    <section className="space-y-4 animate-fade-up">
      {/* ── Document header ──────────────────────────────── */}
      <div className="card px-5 py-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-1.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">{docLabel}</h2>
              <Badge variant={confVariant(confPct)}>{confPct}% confidence</Badge>
              {status && (
                <Badge variant={statusVariant(status)}>{currentStatus.label}</Badge>
              )}
            </div>
            <p className="text-xs text-slate-400 font-medium">Extracted {createdAt}</p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
            {/* Follow-up status selector */}
            <div className="relative">
              <select
                value={status ?? ""}
                disabled={savingStatus}
                onChange={(e) => handleStatus((e.target.value || null) as FollowUpStatus)}
                aria-label="Set follow-up status"
                className="appearance-none text-xs font-semibold px-3 py-1.5 pr-7 rounded-lg border bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200 hover:border-slate-300 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                {STATUS_OPTIONS.map((o) => (
                  <option key={String(o.value)} value={o.value ?? ""}>
                    {o.label}
                  </option>
                ))}
              </select>
              <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
              </svg>
            </div>

            {/* Export CSV */}
            <a
              href={exportCsvUrl(extraction.doc_type)}
              download
              aria-label="Export records as CSV"
              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200 hover:border-slate-300 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Export CSV
            </a>

            {/* Copy JSON */}
            <button
              onClick={copyJSON}
              aria-label="Copy extraction as JSON"
              className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all duration-200 ${
                copied
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200 hover:border-slate-300"
              }`}
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy JSON
                </>
              )}
            </button>

            {/* Overlay toggle */}
            <button
              onClick={() => setShowOverlay((v) => !v)}
              aria-label={showOverlay ? "Hide document overlay" : "Show document overlay"}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200 hover:border-slate-300 transition-colors"
            >
              {showOverlay ? "Hide" : "Show"} overlay
            </button>
          </div>
        </div>
      </div>

      {/* ── Overlay image ────────────────────────────────── */}
      {showOverlay && (
        <div className="card overflow-hidden animate-scale-in">
          <div className="bg-slate-50 flex items-center justify-center p-4" style={{ minHeight: 180 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={overlayUrl(extraction.id)}
              alt={`Extraction overlay for ${docLabel}`}
              className="max-w-full max-h-96 object-contain rounded-lg"
            />
          </div>
          <div className="px-5 py-2.5 border-t border-slate-100">
            <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-widest">
              Document with detected field regions
            </p>
          </div>
        </div>
      )}

      {/* ── Fields panel ─────────────────────────────────── */}
      <div className="card overflow-hidden">
        <div className="px-5 py-3 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
            Extracted Fields
          </h3>
          <span className="text-[11px] text-slate-400 font-medium">
            {fields.length} field{fields.length !== 1 ? "s" : ""}
          </span>
        </div>

        <table className="w-full text-sm" role="grid" aria-label="Extracted document fields">
          <thead className="sr-only">
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Value</th>
              <th scope="col">Confidence</th>
              <th scope="col">Capture type</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {fields.map((f) => (
              <FieldRow
                key={f.name}
                field={f}
                saving={savingField === f.name}
                onChange={handleChange}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
