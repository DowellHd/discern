import type { BatchOut, Extraction, FollowUpStatus, SearchResponse, Stats, TemplatesResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function _json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function extractDocument(file: File, docType?: string): Promise<Extraction> {
  const form = new FormData();
  form.append("file", file);
  if (docType) form.append("doc_type", docType);
  return _json(await fetch(`${BASE}/extract`, { method: "POST", body: form }));
}

export async function extractBatch(files: File[]): Promise<BatchOut> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return _json(await fetch(`${BASE}/extract/batch`, { method: "POST", body: form }));
}

export async function searchDocuments(
  q?: string,
  doc_type?: string,
  follow_up_status?: string,
  limit = 20,
  offset = 0
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (doc_type) params.set("doc_type", doc_type);
  if (follow_up_status) params.set("follow_up_status", follow_up_status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return _json(await fetch(`${BASE}/search?${params}`));
}

export async function patchField(
  id: string,
  fieldName: string,
  value: string | null
): Promise<Extraction> {
  return _json(
    await fetch(`${BASE}/extractions/${id}/fields/${fieldName}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    })
  );
}

export async function patchStatus(
  id: string,
  follow_up_status: FollowUpStatus
): Promise<Extraction> {
  return _json(
    await fetch(`${BASE}/extractions/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ follow_up_status }),
    })
  );
}

export async function deleteExtraction(id: string): Promise<void> {
  const res = await fetch(`${BASE}/extractions/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

export async function getStats(): Promise<Stats> {
  return _json(await fetch(`${BASE}/stats`));
}

export async function getTemplates(): Promise<TemplatesResponse> {
  return _json(await fetch(`${BASE}/templates`));
}

export function exportCsvUrl(doc_type?: string): string {
  const params = doc_type ? `?doc_type=${encodeURIComponent(doc_type)}` : "";
  return `${BASE}/export.csv${params}`;
}

export function overlayUrl(id: string): string {
  return `${BASE}/extractions/${id}/overlay`;
}

export function exportVcardUrl(id: string): string {
  return `${BASE}/extractions/${id}/export.vcf`;
}

export function exportIcalUrl(id: string): string {
  return `${BASE}/extractions/${id}/export.ics`;
}

export function exportExpenseUrl(id: string): string {
  return `${BASE}/extractions/${id}/export-expense.csv`;
}

export async function getReviewQueue(
  threshold = 0.7,
  limit = 20,
  offset = 0
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    threshold: String(threshold),
    limit: String(limit),
    offset: String(offset),
  });
  return _json(await fetch(`${BASE}/review?${params}`));
}
