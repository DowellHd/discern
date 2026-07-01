export type FollowUpStatus = "pending" | "contacted" | "done" | null;

export interface TemplateField {
  name: string;
  value_type: string;
  capture: string;
  options: string[] | null;
  required: boolean;
  nullable: boolean;
  sensitive: boolean;
}

export interface ExportHints {
  format: string;
  date_field: string | null;
  amount_field: string | null;
  title_field: string | null;
}

export interface Template {
  key: string;
  label: string;
  category: string;
  description: string;
  fields: TemplateField[];
  export_hints: ExportHints | null;
}

export interface TemplatesResponse {
  templates: Template[];
}

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
  template_category: string | null;
  fields: Field[];
  overlay_url: string;
  created_at: string;
  follow_up_status: FollowUpStatus;
  llm_refined: boolean;
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
