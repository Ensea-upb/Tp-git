"use client";

import { useState, useTransition } from "react";
import type { OfferLLMAnalysis } from "@/types/analysis";
import { triggerOfferAnalysis } from "@/lib/api";

interface Props {
  offerId: string;
  analysis: OfferLLMAnalysis | null;
}

export default function LLMAnalysisPanel({ offerId, analysis }: Props) {
  const [isPending, startTransition] = useTransition();
  const [localAnalysis, setLocalAnalysis] = useState(analysis);
  const [error, setError] = useState<string | null>(null);
  const [queued, setQueued] = useState(false);

  const handleTrigger = () => {
    setError(null);
    startTransition(async () => {
      try {
        await triggerOfferAnalysis(offerId);
        setQueued(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erreur inconnue");
      }
    });
  };

  const statusColor = (status: string) => {
    if (status === "DONE") return "text-green-700";
    if (status === "FAILED") return "text-red-600";
    if (status === "RUNNING") return "text-blue-600";
    return "text-gray-500";
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-800">Analyse IA</h2>
        {(!localAnalysis || localAnalysis.analysis_status === "FAILED") && (
          <button
            onClick={handleTrigger}
            disabled={isPending || queued}
            className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? "Lancement…" : queued ? "En attente…" : "Analyser"}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-600 mb-2">
          {error.includes("503") ? "Ollama non disponible. Est-il lancé ?" : error}
        </p>
      )}

      {queued && !localAnalysis && (
        <p className="text-xs text-blue-600 italic">
          Analyse lancée en arrière-plan. Rechargez la page dans quelques secondes.
        </p>
      )}

      {localAnalysis && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Statut :</span>
            <span className={`text-xs font-medium ${statusColor(localAnalysis.analysis_status)}`}>
              {localAnalysis.analysis_status}
            </span>
            <span className="text-xs text-gray-300">·</span>
            <span className="text-xs text-gray-400">{localAnalysis.model_used}</span>
          </div>

          {localAnalysis.summary && (
            <p className="text-sm text-gray-700 italic leading-relaxed">
              {localAnalysis.summary}
            </p>
          )}

          {localAnalysis.missions && localAnalysis.missions.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Missions
              </p>
              <ul className="space-y-0.5">
                {localAnalysis.missions.map((m, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                    <span className="mt-0.5 shrink-0">·</span>
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {localAnalysis.skills_required && localAnalysis.skills_required.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Compétences requises
              </p>
              <div className="flex flex-wrap gap-1">
                {localAnalysis.skills_required.map((s, i) => (
                  <span
                    key={i}
                    className="text-xs bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded-full"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {localAnalysis.tech_stack && localAnalysis.tech_stack.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Stack technique
              </p>
              <div className="flex flex-wrap gap-1">
                {localAnalysis.tech_stack.map((t, i) => (
                  <span
                    key={i}
                    className="text-xs bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {localAnalysis.seniority_level && (
            <p className="text-xs text-gray-500">
              Niveau : <span className="font-medium text-gray-700">{localAnalysis.seniority_level}</span>
            </p>
          )}
        </div>
      )}

      {!localAnalysis && !queued && (
        <p className="text-xs text-gray-400 italic">
          Aucune analyse disponible. Cliquez sur &ldquo;Analyser&rdquo; pour lancer.
        </p>
      )}
    </div>
  );
}
