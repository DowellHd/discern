export type FollowUpStatus = "pending" | "contacted" | "done" | null;

export interface Field {
  name: string;
  value: string | null;
  confidence: number;
  capture: string;
  sensitive: boolean;
  corrected: boolean;
}

export interface Extraction {
  id: string;
  doc_type: string;
  doc_type_confidence: number;
  fields: Field[];
  overlay_url: string;
  created_at: string;
  follow_up_status: FollowUpStatus;
}

export interface SearchResponse {
  total: number;
  results: Extraction[];
}

export interface BatchOut {
  results: Extraction[];
  errors: string[];
}

export interface Stats {
  total_documents: number;
  by_doc_type: Record<string, number>;
  avg_confidence: number;
  review_queue: number;
}
