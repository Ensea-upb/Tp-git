"use client";

import { useEffect, useState } from "react";
import { getStrategyRecommendations } from "@/lib/api";
import type { StrategyRecommendations, StrategyActionType } from "@/types/strategy";

const ACTION_ICONS: Record<StrategyActionType, string> = {
  APPLY_NOW: "🚀",
  SEND_FOLLOWUP: "📬",
  PREPARE_INTERVIEW: "🎯",
  ARCHIVE_STALE: "🗃️",
};

const ACTION_LABELS: Record<StrategyActionType, string> = {
  APPLY_NOW: "Postuler",
  SEND_FOLLOWUP: "Relancer",
  PREPARE_INTERVIEW: "Préparer",
  ARCHIVE_STALE: "Archiver",
};

const PRIORITY_COLORS: Record<number, string> = {
  1: "bg-gray-100 text-gray-600",
  2: "bg-yellow-100 text-yellow-700",
  3: "bg-red-100 text-red-700",
};

const PRIORITY_LABELS: Record<number, string> = {
  1: "Faible",
  2: "Moyen",
  3: "Élevé",
};

export default function StrategyPanel() {
  const [data, setData] = useState<StrategyRecommendations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const result = await getStrategyRecommendations(10);
        setData(result);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Erreur lors du chargement des recommandations."
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <p className="text-xs text-gray-400 py-2">Chargement des recommandations…</p>;
  }

  if (error) {
    return <p className="text-xs text-red-500 py-2">{error}</p>;
  }

  if (!data) return null;

  const totalActions = data.actions.length;
  const totalOffers = data.prioritized_offers.length;
  const totalGaps = data.skill_gaps.length;

  return (
    <div className="space-y-6">
      {/* En-tête résumé */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-blue-50 rounded-lg p-3">
          <p className="text-2xl font-bold text-blue-700">{totalActions}</p>
          <p className="text-xs text-blue-500">Actions</p>
        </div>
        <div className="bg-green-50 rounded-lg p-3">
          <p className="text-2xl font-bold text-green-700">{totalOffers}</p>
          <p className="text-xs text-green-500">Offres prioritaires</p>
        </div>
        <div className="bg-orange-50 rounded-lg p-3">
          <p className="text-2xl font-bold text-orange-700">{totalGaps}</p>
          <p className="text-xs text-orange-500">Skill gaps</p>
        </div>
      </div>

      {/* Actions recommandées */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Actions du jour
        </h3>
        {data.actions.length === 0 ? (
          <p className="text-xs text-gray-400">Aucune action recommandée pour le moment.</p>
        ) : (
          <ul className="space-y-2">
            {data.actions.map((action, i) => (
              <li
                key={i}
                className="flex items-start gap-2 bg-white border border-gray-100 rounded-lg p-2 shadow-sm"
              >
                <span className="text-lg shrink-0">
                  {ACTION_ICONS[action.action_type]}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800">
                    {ACTION_LABELS[action.action_type]}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{action.reason}</p>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
                    PRIORITY_COLORS[action.priority] ?? "bg-gray-100 text-gray-500"
                  }`}
                >
                  {PRIORITY_LABELS[action.priority] ?? "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Offres prioritaires */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Offres prioritaires
        </h3>
        {data.prioritized_offers.length === 0 ? (
          <p className="text-xs text-gray-400">Aucune offre active disponible.</p>
        ) : (
          <ul className="space-y-1">
            {data.prioritized_offers.slice(0, 5).map((offer) => (
              <li
                key={offer.offer_id}
                className="flex items-center justify-between bg-white border border-gray-100 rounded-lg px-3 py-2 shadow-sm"
              >
                <div className="min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{offer.title}</p>
                  <p className="text-xs text-gray-400">
                    {offer.company_name ?? "—"} · {offer.location_text ?? "—"}
                  </p>
                </div>
                <div className="ml-2 text-right shrink-0">
                  <p className="text-sm font-bold text-blue-600">
                    {offer.priority_score.toFixed(0)}
                  </p>
                  <p className="text-xs text-gray-400">/100</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Skill gaps */}
      {data.skill_gaps.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Compétences à développer
          </h3>
          <ul className="space-y-2">
            {data.skill_gaps.map((gap) => (
              <li
                key={gap.offer_id}
                className="bg-white border border-gray-100 rounded-lg px-3 py-2 shadow-sm"
              >
                <p className="text-xs font-medium text-gray-700 mb-1">{gap.offer_title}</p>
                <div className="flex flex-wrap gap-1">
                  {gap.missing_skills.slice(0, 8).map((skill) => (
                    <span
                      key={skill}
                      className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded"
                    >
                      {skill}
                    </span>
                  ))}
                  {gap.missing_skills.length > 8 && (
                    <span className="text-xs text-gray-400">
                      +{gap.missing_skills.length - 8}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
