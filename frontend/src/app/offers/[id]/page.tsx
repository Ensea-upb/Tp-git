import Link from "next/link";
import { notFound } from "next/navigation";
import { getOffer } from "@/lib/api";
import { WORK_MODE_LABELS } from "@/lib/constants";
import StateChip from "@/components/StateChip";

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

function ScoreBar({ score, label }: { score: number; label: string }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">{label}</span>
        <span className="font-bold text-gray-800">{pct.toFixed(0)} / 100</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
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

        {/* Métadonnées en grille */}
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
        <div className="lg:col-span-2">
          {offer.normalized_description && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Description du poste</h2>
              <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                {offer.normalized_description}
              </div>
            </div>
          )}
        </div>

        {/* Scoring */}
        <div className="space-y-4">
          {(offer.global_score != null || offer.action_score != null) && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Score de pertinence</h2>
              <div className="space-y-4">
                {offer.global_score != null && (
                  <ScoreBar score={offer.global_score} label="Score global" />
                )}
                {offer.action_score != null && (
                  <ScoreBar score={offer.action_score} label="Score d'action" />
                )}
              </div>
            </div>
          )}

          {offer.score_justification && (
            <div className="bg-white rounded-lg border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Analyse</h2>
              <div className="space-y-3 text-sm">
                {offer.score_justification.résumé && (
                  <p className="text-gray-700 italic">{offer.score_justification.résumé}</p>
                )}

                {offer.score_justification.points_forts &&
                  offer.score_justification.points_forts.length > 0 && (
                    <div>
                      <p className="font-medium text-green-700 mb-1">Points forts</p>
                      <ul className="space-y-0.5">
                        {offer.score_justification.points_forts.map((pt, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-gray-700">
                            <span className="text-green-500 mt-0.5">✓</span>
                            {pt}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                {offer.score_justification.points_faibles &&
                  offer.score_justification.points_faibles.length > 0 && (
                    <div>
                      <p className="font-medium text-orange-700 mb-1">Points d&apos;attention</p>
                      <ul className="space-y-0.5">
                        {offer.score_justification.points_faibles.map((pt, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-gray-700">
                            <span className="text-orange-400 mt-0.5">△</span>
                            {pt}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                {offer.score_justification.recommandation && (
                  <div className="bg-blue-50 rounded p-3 mt-2">
                    <p className="text-xs font-medium text-blue-700 mb-0.5">Recommandation</p>
                    <p className="text-blue-800 text-xs">{offer.score_justification.recommandation}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Actions (placeholder Sprint 4) */}
          <div className="bg-white rounded-lg border border-dashed border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-400 mb-3">Actions</h2>
            <div className="space-y-2">
              <button
                disabled
                title="Disponible Sprint 4"
                className="w-full px-4 py-2 text-sm bg-gray-100 text-gray-400 rounded-lg cursor-not-allowed"
              >
                Préparer la candidature
              </button>
              <button
                disabled
                title="Disponible Sprint 4"
                className="w-full px-4 py-2 text-sm border border-dashed border-gray-200 text-gray-400 rounded-lg cursor-not-allowed"
              >
                Rejeter l&apos;offre
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-3 text-center">Disponible Sprint 4</p>
          </div>
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
