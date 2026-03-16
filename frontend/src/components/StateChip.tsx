import type { OfferState } from "@/types/offer";

interface StateChipProps {
  state: OfferState;
}

const STATE_CONFIG: Record<OfferState, { label: string; className: string }> = {
  DETECTED: { label: "Détectée", className: "bg-gray-100 text-gray-700" },
  RAW_STORED: { label: "Stockée", className: "bg-gray-100 text-gray-600" },
  NORMALIZED: { label: "Normalisée", className: "bg-blue-100 text-blue-700" },
  DEDUPLICATED: { label: "Dédupliquée", className: "bg-blue-100 text-blue-600" },
  ANALYZED: { label: "Analysée", className: "bg-indigo-100 text-indigo-700" },
  REJECTED: { label: "Rejetée", className: "bg-red-100 text-red-700" },
  QUALIFIED: { label: "Qualifiée", className: "bg-green-100 text-green-700" },
  DRAFT_REQUESTED: { label: "Brouillon demandé", className: "bg-yellow-100 text-yellow-700" },
  DRAFT_PREPARED: { label: "Brouillon prêt", className: "bg-yellow-200 text-yellow-800" },
  READY_FOR_REVIEW: { label: "À valider", className: "bg-orange-100 text-orange-700" },
  SUBMISSION_IN_PROGRESS: { label: "En soumission", className: "bg-purple-100 text-purple-700" },
  SUBMITTED: { label: "Soumise", className: "bg-purple-200 text-purple-800" },
  CLOSED: { label: "Clôturée", className: "bg-gray-200 text-gray-500" },
};

export default function StateChip({ state }: StateChipProps) {
  const config = STATE_CONFIG[state] ?? { label: state, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}
