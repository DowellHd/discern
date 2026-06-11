import type { Extraction, SearchResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function extractDocument(file: File): Promise<Extraction> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/extract`, { method: "POST", body: form });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function searchDocuments(
  q?: string,
  doc_type?: string,
  limit = 20,
  offset = 0
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (doc_type) params.set("doc_type", doc_type);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const res = await fetch(`${BASE}/search?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function overlayUrl(id: string): string {
  return `${BASE}/extractions/${id}/overlay`;
}
