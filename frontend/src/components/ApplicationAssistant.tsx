"use client";

import { useState } from "react";
import type { AssistantResult } from "@/types/analysis";
import {
  generateCoverLetter,
  generateApplicationEmail,
  generateInterviewPrep,
} from "@/lib/api";

interface Props {
  offerId: string;
}

type Mode = "cover-letter" | "email" | "interview" | null;

export default function ApplicationAssistant({ offerId }: Props) {
  const [mode, setMode] = useState<Mode>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AssistantResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (selectedMode: Mode) => {
    if (!selectedMode) return;
    setMode(selectedMode);
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      let data: AssistantResult;
      if (selectedMode === "cover-letter") {
        data = await generateCoverLetter(offerId);
      } else if (selectedMode === "email") {
        data = await generateApplicationEmail(offerId);
      } else {
        data = await generateInterviewPrep(offerId);
      }
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erreur inconnue";
      setError(msg.includes("503") ? "Ollama non disponible. Est-il lancé ?" : msg);
    } finally {
      setLoading(false);
    }
  };

  const btnClass = (m: Mode) =>
    `text-xs px-3 py-1.5 rounded-lg border transition-colors ${
      mode === m
        ? "bg-blue-600 text-white border-blue-600"
        : "bg-white text-gray-600 border-gray-200 hover:border-blue-400 hover:text-blue-700"
    }`;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h2 className="text-base font-semibold text-gray-800 mb-3">Assistant candidature</h2>

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => handleGenerate("cover-letter")}
          disabled={loading}
          className={btnClass("cover-letter")}
        >
          Lettre de motivation
        </button>
        <button
          onClick={() => handleGenerate("email")}
          disabled={loading}
          className={btnClass("email")}
        >
          Email
        </button>
        <button
          onClick={() => handleGenerate("interview")}
          disabled={loading}
          className={btnClass("interview")}
        >
          Entretien
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="animate-spin">⟳</span>
          Génération en cours…
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-xs text-red-700">{error}</p>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-3">
          {/* Cover letter or email */}
          {(result.subject || result.body) && (
            <div className="space-y-2">
              {result.subject && (
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-0.5">
                    Objet
                  </p>
                  <p className="text-sm font-medium text-gray-800">{result.subject}</p>
                </div>
              )}
              {result.body && (
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-0.5">
                    Corps
                  </p>
                  <div className="bg-gray-50 border border-gray-100 rounded-lg p-3">
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                      {result.body}
                    </pre>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(result.body!)}
                    className="mt-1.5 text-xs text-blue-600 hover:underline"
                  >
                    Copier
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Interview prep */}
          {result.technical_questions && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Questions techniques
              </p>
              <ol className="space-y-1">
                {result.technical_questions.map((q, i) => (
                  <li key={i} className="text-xs text-gray-700">
                    {i + 1}. {q}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {result.behavioral_questions && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Questions comportementales
              </p>
              <ol className="space-y-1">
                {result.behavioral_questions.map((q, i) => (
                  <li key={i} className="text-xs text-gray-700">
                    {i + 1}. {q}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {result.questions_to_ask && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Questions à poser
              </p>
              <ul className="space-y-0.5">
                {result.questions_to_ask.map((q, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                    <span className="mt-0.5 shrink-0">·</span>
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.preparation_tips && (
            <div className="bg-amber-50 border border-amber-100 rounded-lg p-3">
              <p className="text-xs font-medium text-amber-800 mb-1">Conseils</p>
              <ul className="space-y-0.5">
                {result.preparation_tips.map((t, i) => (
                  <li key={i} className="text-xs text-amber-700 flex items-start gap-1">
                    <span className="mt-0.5 shrink-0">·</span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
