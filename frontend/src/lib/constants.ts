import type { WorkMode, OfferState } from "@/types/offer";

export const WORK_MODE_LABELS: Record<WorkMode, string> = {
  ONSITE: "Présentiel",
  HYBRID: "Hybride",
  REMOTE: "Télétravail",
};

export const OFFER_STATE_LABELS: Record<OfferState, string> = {
  DETECTED: "Détectée",
  RAW_STORED: "Stockée",
  NORMALIZED: "Normalisée",
  DEDUPLICATED: "Dédupliquée",
  ANALYZED: "Analysée",
  REJECTED: "Rejetée",
  QUALIFIED: "Qualifiée",
  DRAFT_REQUESTED: "Brouillon demandé",
  DRAFT_PREPARED: "Brouillon prêt",
  READY_FOR_REVIEW: "À valider",
  SUBMISSION_IN_PROGRESS: "En soumission",
  SUBMITTED: "Soumise",
  CLOSED: "Clôturée",
};

export const TAG_LABELS: Record<string, string> = {
  data: "Data",
  ml: "ML",
  ai: "AI",
  analytics: "Analytics",
  econometrics: "Économétrie",
};

export const TAG_COLORS: Record<string, string> = {
  data: "bg-blue-50 text-blue-700 border-blue-200",
  ml: "bg-purple-50 text-purple-700 border-purple-200",
  ai: "bg-violet-50 text-violet-700 border-violet-200",
  analytics: "bg-cyan-50 text-cyan-700 border-cyan-200",
  econometrics: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

export const CONTRACT_TYPE_OPTIONS = [
  { value: "", label: "Tous les contrats" },
  { value: "Stage", label: "Stage" },
  { value: "Alternance", label: "Alternance" },
  { value: "CDI", label: "CDI" },
  { value: "CDD", label: "CDD" },
  { value: "Freelance", label: "Freelance" },
];

export const WORK_MODE_OPTIONS = [
  { value: "", label: "Tous les modes" },
  { value: "ONSITE", label: "Présentiel" },
  { value: "HYBRID", label: "Hybride" },
  { value: "REMOTE", label: "Télétravail" },
];

export const SORT_OPTIONS = [
  { value: "created_at", label: "Date d'ajout" },
  { value: "relevance_score", label: "Score de pertinence" },
];
