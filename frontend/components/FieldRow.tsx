"use client";
import { useState } from "react";
import type { Field } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";

interface Props {
  field: Field;
  onChange: (name: string, value: string) => void;
}

function confVariant(conf: number): BadgeVariant {
  if (conf >= 0.75) return "success";
  if (conf >= 0.45) return "warn";
  return "danger";
}

function CaptureIcon({ type }: { type: string }) {
  if (type === "handwritten") {
    return (
      <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
      </svg>
    );
  }
  if (type === "checkbox") {
    return (
      <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
    );
  }
  return (
    <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h8" />
    </svg>
  );
}

export function FieldRow({ field, onChange }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(field.value ?? "");

  const label = field.name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  const isRedacted = field.sensitive && field.value === "[REDACTED]";
  const displayVal = isRedacted ? "••••••" : (field.value ?? "—");
  const isEmpty = !field.value;
  const canEdit = !isRedacted && field.capture !== "handwritten";
  const confPct = Math.round(field.confidence * 100);

  function commit() {
    setEditing(false);
    onChange(field.name, draft);
  }

  return (
    <tr className="group hover:bg-slate-50/60 transition-colors duration-100">
      {/* Label */}
      <td className="py-3 pl-5 pr-3 w-36 sm:w-40 align-top">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wide leading-none">
          {label}
        </span>
      </td>

      {/* Value */}
      <td className="py-3 px-3 align-top">
        {editing ? (
          <input
            autoFocus
            className="w-full border border-indigo-300 rounded-lg px-2.5 py-1 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-shadow"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") { setEditing(false); setDraft(field.value ?? ""); }
            }}
            aria-label={`Edit ${label}`}
          />
        ) : (
          <span
            className={`
              text-sm block leading-relaxed
              ${isEmpty
                ? "text-slate-300 italic"
                : isRedacted
                  ? "text-slate-400 font-mono tracking-widest"
                  : "text-slate-800 font-medium"
              }
              ${canEdit ? "cursor-text hover:text-indigo-700 transition-colors duration-100" : ""}
            `}
            onClick={() => { if (canEdit) setEditing(true); }}
            role={canEdit ? "button" : undefined}
            tabIndex={canEdit ? 0 : undefined}
            onKeyDown={(e) => {
              if (canEdit && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                setEditing(true);
              }
            }}
            title={canEdit ? "Click to edit" : undefined}
            aria-label={canEdit ? `${label}: ${displayVal}. Click to edit.` : undefined}
          >
            {displayVal}
          </span>
        )}
      </td>

      {/* Confidence */}
      <td className="py-3 px-3 whitespace-nowrap align-top">
        <div className="flex items-center gap-1.5">
          {/* Mini bar */}
          <div
            className="w-10 h-1.5 rounded-full bg-slate-100 overflow-hidden flex-shrink-0"
            aria-hidden="true"
          >
            <div
              className={`h-full rounded-full ${
                field.confidence >= 0.75
                  ? "bg-emerald-400"
                  : field.confidence >= 0.45
                    ? "bg-amber-400"
                    : "bg-red-400"
              }`}
              style={{ width: `${confPct}%` }}
            />
          </div>
          <Badge
            variant={confVariant(field.confidence)}
            className="tabular-nums"
          >
            {confPct}%
          </Badge>
        </div>
      </td>

      {/* Capture type */}
      <td className="py-3 pl-3 pr-5 whitespace-nowrap align-top">
        <Badge variant="neutral" className="gap-1">
          <CaptureIcon type={field.capture} />
          {field.capture}
        </Badge>
      </td>
    </tr>
  );
}
