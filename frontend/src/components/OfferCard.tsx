import Link from "next/link";
import type { OfferListItem } from "@/types/offer";
import { WORK_MODE_LABELS, TAG_LABELS, TAG_COLORS, USER_STATUS_LABELS, USER_STATUS_COLORS } from "@/lib/constants";
import StateChip from "./StateChip";
import OfferActions from "./OfferActions";

interface OfferCardProps {
  offer: OfferListItem;
}

function ScoreBar({ score, label, color }: { score: number; label: string; color?: string }) {
  const pct = Math.min(100, Math.max(0, score));
  const barColor = color ?? (pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400");
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span className="font-semibold text-gray-700">{pct.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
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

  const userStatusValue = offer.user_status?.status ?? null;

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
          <div className="flex items-center gap-2 shrink-0">
            {/* Badge statut utilisateur */}
            {userStatusValue && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${USER_STATUS_COLORS[userStatusValue]}`}
              >
                {USER_STATUS_LABELS[userStatusValue]}
              </span>
            )}
            <StateChip state={offer.current_state} />
          </div>
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

        {/* Scores */}
        <div className="space-y-2 mb-3">
          {offer.ranking_score != null && (
            <ScoreBar
              score={offer.ranking_score}
              label="Pertinence"
              color={
                offer.ranking_score >= 75
                  ? "bg-emerald-500"
                  : offer.ranking_score >= 50
                  ? "bg-emerald-300"
                  : "bg-gray-300"
              }
            />
          )}
          {offer.personalized_score != null && (
            <ScoreBar
              score={offer.personalized_score}
              label="Score personnalisé"
              color={
                offer.personalized_score >= 80
                  ? "bg-blue-500"
                  : offer.personalized_score >= 60
                  ? "bg-blue-300"
                  : "bg-gray-300"
              }
            />
          )}
          {offer.global_score != null && (
            <ScoreBar score={offer.global_score} label="Score global" />
          )}
        </div>

        {/* Pied de carte : source + actions */}
        <div className="flex items-center justify-between mt-2">
          {offer.primary_source && (
            <p className="text-xs text-gray-400">Source : {offer.primary_source.name}</p>
          )}
          <OfferActions
            offerId={offer.id}
            currentStatus={userStatusValue}
            compact
          />
        </div>
      </div>
    </Link>
  );
}
