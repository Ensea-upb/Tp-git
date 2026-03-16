import Link from "next/link";
import type { OfferListItem } from "@/types/offer";
import { WORK_MODE_LABELS, TAG_LABELS, TAG_COLORS } from "@/lib/constants";
import StateChip from "./StateChip";

interface OfferCardProps {
  offer: OfferListItem;
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-semibold text-gray-700 w-8 text-right">{pct.toFixed(0)}</span>
    </div>
  );
}

function TagBadge({ tag }: { tag: string }) {
  const label = TAG_LABELS[tag] ?? tag;
  const colorClass = TAG_COLORS[tag] ?? "bg-gray-50 text-gray-600 border-gray-200";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {label}
    </span>
  );
}

export default function OfferCard({ offer }: OfferCardProps) {
  const publishedDate = offer.published_at
    ? new Date(offer.published_at).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <Link href={`/offers/${offer.id}`} className="block group">
      <div className="bg-white border border-gray-200 rounded-lg p-5 hover:border-blue-400 hover:shadow-md transition-all duration-150">
        {/* En-tête */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-gray-900 group-hover:text-blue-700 truncate">
              {offer.normalized_title}
            </h2>
            {offer.company && (
              <p className="text-sm text-gray-600 mt-0.5">{offer.company.name}</p>
            )}
          </div>
          <StateChip state={offer.current_state} />
        </div>

        {/* Métadonnées */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 mb-3">
          {offer.contract_type && (
            <span className="flex items-center gap-1">
              <span className="font-medium text-gray-600">{offer.contract_type}</span>
              {offer.duration_months && <span>· {offer.duration_months} mois</span>}
            </span>
          )}
          {offer.location_text && <span>📍 {offer.location_text}</span>}
          {offer.work_mode && (
            <span>🏢 {WORK_MODE_LABELS[offer.work_mode] ?? offer.work_mode}</span>
          )}
          {publishedDate && <span>Publié le {publishedDate}</span>}
        </div>

        {/* Tags métier */}
        {offer.tags && offer.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {offer.tags.map((tag) => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        )}

        {/* Score de pertinence */}
        {offer.global_score != null && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-0.5">
              <span>Score de pertinence</span>
              <span className="text-gray-400">/ 100</span>
            </div>
            <ScoreBar score={offer.global_score} />
          </div>
        )}

        {/* Source */}
        {offer.primary_source && (
          <p className="text-xs text-gray-400 mt-3">
            Source : {offer.primary_source.name}
          </p>
        )}
      </div>
    </Link>
  );
}
