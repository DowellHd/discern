"use client";
import { useState } from "react";
import type { Field } from "@/lib/types";

interface Props {
  field: Field;
  onChange: (name: string, value: string) => void;
}

function confidenceColor(conf: number): string {
  if (conf >= 0.75) return "bg-emerald-100 text-emerald-700";
  if (conf >= 0.45) return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-600";
}

export function FieldRow({ field, onChange }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(field.value ?? "");

  const label = field.name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const isRedacted = field.sensitive && field.value === "[REDACTED]";
  const displayVal = isRedacted ? "••••••" : (field.value ?? "—");

  return (
    <tr className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
      <td className="py-2.5 px-4 text-sm text-slate-500 whitespace-nowrap">{label}</td>
      <td className="py-2.5 px-4 text-sm font-medium text-slate-800">
        {editing ? (
          <input
            autoFocus
            className="w-full border border-indigo-300 rounded px-2 py-0.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              setEditing(false);
              onChange(field.name, draft);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") { setEditing(false); onChange(field.name, draft); }
              if (e.key === "Escape") setEditing(false);
            }}
          />
        ) : (
          <span
            className={`${!isRedacted && field.capture !== "handwritten" ? "cursor-text hover:underline decoration-dashed" : ""}`}
            title={!isRedacted && field.capture !== "handwritten" ? "Click to edit" : undefined}
            onClick={() => { if (!isRedacted) setEditing(true); }}
          >
            {displayVal}
          </span>
        )}
      </td>
      <td className="py-2.5 px-4 text-xs whitespace-nowrap">
        <span className={`px-2 py-0.5 rounded-full font-semibold ${confidenceColor(field.confidence)}`}>
          {(field.confidence * 100).toFixed(0)}%
        </span>
      </td>
      <td className="py-2.5 px-4 text-xs text-slate-400 whitespace-nowrap">{field.capture}</td>
    </tr>
  );
}
