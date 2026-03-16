"use client";

import { useState, useTransition } from "react";
import type { ProfileMatch } from "@/types/analysis";
import { triggerProfileMatch } from "@/lib/api";

interface Props {
  offerId: string;
  match: ProfileMatch | null;
}

function MatchScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 75 ? "bg-green-500" : pct >= 50 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">Compatibilité profil</span>
        <span className="font-bold text-gray-800">{pct.toFixed(0)} / 100</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ProfileMatchPanel({ offerId, match }: Props) {
  const [isPending, startTransition] = useTransition();
  const [queued, setQueued] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrigger = () => {
    setError(null);
    startTransition(async () => {
      try {
        await triggerProfileMatch(offerId);
        setQueued(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erreur inconnue");
      }
    });
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-800">Compatibilité profil</h2>
        {(!match || match.match_status === "FAILED") && (
          <button
            onClick={handleTrigger}
            disabled={isPending || queued}
            className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? "Lancement…" : queued ? "En attente…" : "Évaluer"}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-600 mb-2">
          {error.includes("503") ? "Ollama non disponible." : error}
        </p>
      )}

      {queued && !match && (
        <p className="text-xs text-indigo-600 italic">
          Évaluation lancée. Rechargez dans quelques secondes.
        </p>
      )}

      {match && match.match_status === "DONE" && (
        <div className="space-y-3">
          {match.match_score != null && <MatchScoreBar score={match.match_score} />}

          {match.strengths && match.strengths.length > 0 && (
            <div>
              <p className="text-xs font-medium text-green-700 uppercase tracking-wide mb-1">
                Points forts
              </p>
              <ul className="space-y-0.5">
                {match.strengths.map((s, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                    <span className="text-green-500 mt-0.5 shrink-0">✓</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {match.gaps && match.gaps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-orange-700 uppercase tracking-wide mb-1">
                Points à améliorer
              </p>
              <ul className="space-y-0.5">
                {match.gaps.map((g, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                    <span className="text-orange-400 mt-0.5 shrink-0">△</span>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {match.recommendation && (
            <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3">
              <p className="text-xs text-indigo-800 italic">{match.recommendation}</p>
            </div>
          )}

          <p className="text-xs text-gray-400">Modèle : {match.model_used}</p>
        </div>
      )}

      {match && match.match_status === "FAILED" && (
        <p className="text-xs text-red-500 italic">Évaluation échouée. Réessayez.</p>
      )}

      {!match && !queued && (
        <p className="text-xs text-gray-400 italic">
          Cliquez sur &ldquo;Évaluer&rdquo; pour comparer avec votre profil.
        </p>
      )}
    </div>
  );
}
