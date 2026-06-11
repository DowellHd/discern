export interface Field {
  name: string;
  value: string | null;
  confidence: number;
  capture: string;
  sensitive: boolean;
}

export interface Extraction {
  id: string;
  doc_type: string;
  doc_type_confidence: number;
  fields: Field[];
  overlay_url: string;
  created_at: string;
}

export interface SearchResponse {
  total: number;
  results: Extraction[];
}
