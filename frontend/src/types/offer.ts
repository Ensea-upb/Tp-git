// Types TypeScript alignés sur les schémas Pydantic du backend

export type OfferState =
  | "DETECTED"
  | "RAW_STORED"
  | "NORMALIZED"
  | "DEDUPLICATED"
  | "ANALYZED"
  | "REJECTED"
  | "QUALIFIED"
  | "DRAFT_REQUESTED"
  | "DRAFT_PREPARED"
  | "READY_FOR_REVIEW"
  | "SUBMISSION_IN_PROGRESS"
  | "SUBMITTED"
  | "CLOSED";

export type WorkMode = "ONSITE" | "HYBRID" | "REMOTE";

export type SortBy = "created_at" | "relevance_score";

export interface CompanyBrief {
  id: string;
  name: string;
  sector: string | null;
  main_location: string | null;
}

export interface SourceBrief {
  id: string;
  name: string;
  source_type: string;
}

export interface OfferListItem {
  id: string;
  normalized_title: string;
  contract_type: string | null;
  duration_months: number | null;
  location_text: string | null;
  work_mode: WorkMode | null;
  current_state: OfferState;
  is_active: boolean;
  global_score: number | null;
  tags: string[] | null;
  published_at: string | null;
  created_at: string;
  company: CompanyBrief | null;
  primary_source: SourceBrief | null;
}

export interface ScoreJustification {
  score?: number;
  résumé?: string;
  détails?: string[];
  [key: string]: unknown;
}

export interface OfferDetail extends OfferListItem {
  normalized_description: string | null;
  education_level: string | null;
  deadline_at: string | null;
  offer_url: string | null;
  score_justification: ScoreJustification | null;
  updated_at: string;
}

export interface PaginatedOffers {
  items: OfferListItem[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface SourceOut {
  id: string;
  name: string;
  source_type: string;
  base_url: string | null;
  is_active: boolean;
  check_frequency_hours: number;
}
