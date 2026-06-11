"use client";
import { useState } from "react";
import type { Extraction, Field } from "@/lib/types";
import { FieldRow } from "./FieldRow";
import { overlayUrl } from "@/lib/api";

interface Props {
  extraction: Extraction;
}

export function ExtractionResult({ extraction }: Props) {
  const [fields, setFields] = useState<Field[]>(extraction.fields);
  const [showOverlay, setShowOverlay] = useState(true);

  function handleChange(name: string, value: string) {
    setFields((prev) => prev.map((f) => (f.name === name ? { ...f, value } : f)));
  }

  const docLabel = extraction.doc_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const confPct = (extraction.doc_type_confidence * 100).toFixed(1);
  const createdAt = new Date(extraction.created_at).toLocaleString();

  return (
    <section className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">{docLabel}</h2>
          <p className="text-xs text-slate-500">
            {confPct}% confidence · {createdAt}
          </p>
        </div>
        <button
          onClick={() => setShowOverlay((v) => !v)}
          className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600"
        >
          {showOverlay ? "Hide overlay" : "Show overlay"}
        </button>
      </div>

      {/* Overlay image */}
      {showOverlay && (
        <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-50 flex justify-center p-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={overlayUrl(extraction.id)}
            alt="Extraction overlay"
            className="max-w-full max-h-80 object-contain rounded-lg"
          />
        </div>
      )}

      {/* Fields table */}
      <div className="rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="py-2 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide w-40">Field</th>
              <th className="py-2 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Value</th>
              <th className="py-2 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide w-16">Conf</th>
              <th className="py-2 px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide w-24">Type</th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {fields.map((f) => (
              <FieldRow key={f.name} field={f} onChange={handleChange} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
