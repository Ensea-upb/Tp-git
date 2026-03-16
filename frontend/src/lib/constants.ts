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
