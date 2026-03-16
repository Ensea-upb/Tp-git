import Link from "next/link";
import { notFound } from "next/navigation";
import { getOffer } from "@/lib/api";
import { WORK_MODE_LABELS, TAG_LABELS, TAG_COLORS } from "@/lib/constants";
import StateChip from "@/components/StateChip";
import OfferActions from "@/components/OfferActions";
import LLMAnalysisPanel from "@/components/LLMAnalysisPanel";
import ProfileMatchPanel from "@/components/ProfileMatchPanel";
import ApplicationAssistant from "@/components/ApplicationAssistant";

interface PageProps {
  params: { id: string };
}

function MetaItem({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-gray-800">{value}</span>
    </div>
  );
}

function ScoreBar({ score, label, color }: { score: number; label: string; color?: string }) {
  const pct = Math.min(100, Math.max(0, score));
  const barColor = color ?? (pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400");
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">{label}</span>
        <span className="font-bold text-gray-800">{pct.toFixed(0)} / 100</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${pct}%` }} />
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

export default async function OfferDetailPage({ params }: PageProps) {
  let offer;
  try {
    offer = await getOffer(params.id);
  } catch (e) {
    if (e instanceof Error && e.message.includes("404")) {
      notFound();
    }
    throw e;
  }

  const publishedDate = offer.published_at
    ? new Date(offer.published_at).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  const deadlineDate = offer.deadline_at
    ? new Date(offer.deadline_at).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500">
        <Link href="/offers" className="hover:text-blue-700">
          Offres
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-800 truncate">{offer.normalized_title}</span>
      </nav>

      {/* En-tête */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-gray-900">{offer.normalized_title}</h1>
            {offer.company && (
              <p className="text-base text-gray-600 mt-1">
                {offer.company.name}
                {offer.company.sector && (
                  <span className="text-gray-400 ml-2">· {offer.company.sector}</span>
                )}
              </p>
            )}
          </div>
          <StateChip state={offer.current_state} />
        </div>

        {/* Tags */}
        {offer.tags && offer.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {offer.tags.map((tag) => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        )}

        {/* Métadonnées */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4 border-t border-b border-gray-100">
          <MetaItem label="Type" value={offer.contract_type} />
          <MetaItem
            label="Durée"
            value={offer.duration_months ? `${offer.duration_months} mois` : null}
          />
          <MetaItem label="Localisation" value={offer.location_text} />
          <MetaItem
            label="Mode"
            value={offer.work_mode ? (WORK_MODE_LABELS[offer.work_mode] ?? offer.work_mode) : null}
          />
          <MetaItem label="Niveau requis" value={offer.education_level} />
          <MetaItem label="Publication" value={publishedDate} />
          <MetaItem label="Date limite" value={deadlineDate} />
          {offer.primary_source && (
            <MetaItem label="Source" value={offer.primary_source.name} />
          )}
        </div>

        {/* Lien externe */}
        {offer.offer_url && (
          <div className="mt-4">
            <a
              href={offer.offer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              Voir l&apos;offre originale
              <span className="text-xs">↗</span>
            </a>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Description */}
        <div className="lg:col-span-2 space-y-4">
          {offer.normalized_description && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Description du poste</h2>
              <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                {offer.normalized_description}
              </div>
            </div>
          )}
        </div>

        {/* Colonne droite */}
        <div className="space-y-4">
          {/* Actions utilisateur */}
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Actions</h2>
            <OfferActions
              offerId={offer.id}
              currentStatus={offer.user_status?.status ?? null}
            />
          </div>

          {/* Scores */}
          {(offer.personalized_score != null || offer.global_score != null) && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Scores</h2>
              <div className="space-y-4">
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
            </div>
          )}

          {/* Justification personnalisée */}
          {offer.personalized_justification?.détails &&
            offer.personalized_justification.détails.length > 0 && (
              <div className="bg-blue-50 rounded-lg border border-blue-100 p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">
                  Détail score personnalisé
                </h3>
                <p className="text-xs text-blue-700 italic mb-2">
                  {offer.personalized_justification.résumé}
                </p>
                <ul className="space-y-0.5">
                  {offer.personalized_justification.détails.map((d, i) => (
                    <li key={i} className="text-xs text-blue-700 flex items-start gap-1">
                      <span className="mt-0.5 shrink-0">·</span>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {/* Analyse globale */}
          {offer.score_justification && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Analyse globale</h2>
              <div className="space-y-3 text-sm">
                {offer.score_justification.résumé && (
                  <p className="text-gray-700 italic">{offer.score_justification.résumé}</p>
                )}
                {offer.score_justification.détails &&
                  offer.score_justification.détails.length > 0 && (
                    <ul className="space-y-0.5">
                      {offer.score_justification.détails.map((d, i) => (
                        <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                          <span className="mt-0.5 shrink-0">·</span>
                          {d}
                        </li>
                      ))}
                    </ul>
                  )}
              </div>
            </div>
          )}

          {/* LLM Analysis */}
          <LLMAnalysisPanel offerId={offer.id} analysis={offer.llm_analysis ?? null} />

          {/* Profile Match */}
          <ProfileMatchPanel offerId={offer.id} match={offer.profile_match ?? null} />

          {/* Application Assistant */}
          <ApplicationAssistant offerId={offer.id} />
        </div>
      </div>

      {/* Retour */}
      <div className="pt-2">
        <Link
          href="/offers"
          className="text-sm text-gray-500 hover:text-blue-700 flex items-center gap-1"
        >
          ← Retour aux offres
        </Link>
      </div>
    </div>
  );
}
