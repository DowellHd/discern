"use client";
import { useState } from "react";
import type { Extraction } from "@/lib/types";
import { searchDocuments } from "@/lib/api";

interface Props {
  onSelect: (extraction: Extraction) => void;
}

export function SearchPanel({ onSelect }: Props) {
  const [q, setQ] = useState("");
  const [docType, setDocType] = useState("");
  const [results, setResults] = useState<Extraction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await searchDocuments(q || undefined, docType || undefined, 20, 0);
      setResults(resp.results);
      setTotal(resp.total);
      setSearched(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          placeholder="Search extracted fields…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
        >
          <option value="">All types</option>
          <option value="connection_card">Connection Card</option>
          <option value="prayer_request">Prayer Request</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          Search
        </button>
      </form>

      {searched && (
        <p className="text-xs text-slate-500">{total} result{total !== 1 ? "s" : ""}</p>
      )}

      <ul className="space-y-1.5">
        {results.map((r) => (
          <li key={r.id}>
            <button
              onClick={() => onSelect(r)}
              className="w-full text-left px-3 py-2.5 rounded-lg border border-slate-200 hover:bg-indigo-50 hover:border-indigo-200 transition-colors"
            >
              <p className="text-sm font-semibold text-slate-800">
                {r.doc_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </p>
              <p className="text-xs text-slate-400">
                {new Date(r.created_at).toLocaleString()} · {(r.doc_type_confidence * 100).toFixed(0)}% conf
              </p>
            </button>
          </li>
        ))}
        {searched && results.length === 0 && (
          <li className="text-sm text-slate-400 text-center py-4">No results found.</li>
        )}
      </ul>
    </div>
  );
}
