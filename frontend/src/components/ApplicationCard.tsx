"use client";

import Link from "next/link";
import type { Application } from "@/types/application";
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_COLORS,
} from "@/types/application";
import { updateApplicationStatus, addFollowup } from "@/lib/api";
import { useState } from "react";
import ApplicationTimeline from "@/components/ApplicationTimeline";

interface Props {
  application: Application;
  onUpdate: () => void;
}

// ── Section brouillons LLM — 3 états distincts ────────────────────────

function DraftSection({ application }: { application: Application }) {
  const [showDraft, setShowDraft] = useState(false);
  const hasDrafts = application.draft_cover_letter || application.draft_email;

  if (!application.drafts_ready) {
    return (
      <p className="text-xs text-gray-400 italic mb-3 flex items-center gap-1.5">
        <span className="inline-block w-2 h-2 rounded-full bg-blue-300 animate-pulse shrink-0" />
        Génération des brouillons en cours…
      </p>
    );
  }

  if (!hasDrafts) {
    return (
      <p className="text-xs text-amber-600 mb-3 flex items-center gap-1.5">
        <span className="shrink-0">⚠</span>
        Brouillons indisponibles (LLM hors ligne lors de la création)
      </p>
    );
  }

  return (
    <div className="mb-3">
      <button
        onClick={() => setShowDraft(!showDraft)}
        className="text-xs text-blue-600 hover:underline"
      >
        {showDraft ? "Masquer brouillons" : "Voir brouillons LLM"}
      </button>
      {showDraft && (
        <div className="mt-2 space-y-2">
          {application.draft_cover_letter && (
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-1">
                Lettre de motivation
              </p>
              <pre className="text-xs bg-gray-50 border rounded p-2 whitespace-pre-wrap max-h-40 overflow-y-auto">
                {application.draft_cover_letter}
              </pre>
            </div>
          )}
          {application.draft_email && (
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-1">Email</p>
              <pre className="text-xs bg-gray-50 border rounded p-2 whitespace-pre-wrap max-h-32 overflow-y-auto">
                {application.draft_email}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Section date de relance — avec sélecteur de date ──────────────────

function FollowupSection({
  applicationId,
  onUpdate,
}: {
  applicationId: string;
  onUpdate: () => void;
}) {
  const defaultDate = (): string => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10); // "YYYY-MM-DD"
  };

  const [date, setDate] = useState<string>(defaultDate);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSchedule() {
    const selectedDate = new Date(date + "T09:00:00");
    if (selectedDate <= new Date()) {
      setError("La date doit être dans le futur.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await addFollowup(applicationId, {
        scheduled_at: selectedDate.toISOString(),
        notes: "Relance planifiée",
      });
      onUpdate();
    } catch {
      setError("Erreur lors de la planification.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2 mt-1">
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-orange-400"
      />
      <button
        onClick={handleSchedule}
        disabled={loading}
        className="text-xs bg-orange-500 text-white px-2 py-1 rounded hover:bg-orange-600 disabled:opacity-50"
      >
        {loading ? "…" : "+ Relance"}
      </button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}

// ── Carte principale ──────────────────────────────────────────────────

export default function ApplicationCard({ application, onUpdate }: Props) {
  const [loading, setLoading] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);

  const statusLabel = APPLICATION_STATUS_LABELS[application.status];
  const statusColor = APPLICATION_STATUS_COLORS[application.status];

  async function transition(target: string) {
    setLoading(true);
    try {
      await updateApplicationStatus(application.id, target as any);
      onUpdate();
    } finally {
      setLoading(false);
    }
  }

  const isTerminal =
    application.status === "REJECTED" ||
    application.status === "ACCEPTED" ||
    application.status === "ARCHIVED";

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* En-tête : titre offre + statut */}
      <div className="flex items-start justify-between gap-2 mb-1">
        <Link
          href={`/offers/${application.offer_id}`}
          className="text-sm font-semibold text-gray-800 hover:text-blue-700 leading-tight"
        >
          {application.offer_title ?? `Offre #${application.offer_id.slice(0, 8)}…`}
        </Link>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${statusColor}`}>
          {statusLabel}
        </span>
      </div>

      {/* Source de l'offre */}
      {application.offer_source_name && (
        <p className="text-xs text-gray-400 mb-2">
          via <span className="font-medium text-gray-500">{application.offer_source_name}</span>
        </p>
      )}

      {/* Canal de candidature & notes */}
      {application.source_channel && (
        <p className="text-xs text-gray-500 mb-1">
          Canal : <span className="font-medium">{application.source_channel}</span>
        </p>
      )}
      {application.notes && (
        <p className="text-xs text-gray-500 mb-2 line-clamp-2">{application.notes}</p>
      )}

      {/* Date de candidature */}
      {application.applied_at && (
        <p className="text-xs text-gray-400 mb-2">
          Envoyé le {new Date(application.applied_at).toLocaleDateString("fr-FR")}
        </p>
      )}

      {/* Relances planifiées */}
      {application.followups.length > 0 && (
        <p className="text-xs text-orange-600 mb-2">
          {application.followups.length} relance(s) planifiée(s)
        </p>
      )}

      {/* Brouillons LLM */}
      <DraftSection application={application} />

      {/* Actions contextuelles — désactivées sur états terminaux */}
      {!isTerminal && (
        <div className="flex flex-col gap-2 mt-2">
          {application.status === "DRAFT" && (
            <button
              onClick={() => transition("READY_TO_SEND")}
              disabled={loading}
              className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600 disabled:opacity-50"
            >
              Prêt à envoyer
            </button>
          )}
          {application.status === "READY_TO_SEND" && (
            <button
              onClick={() => transition("SENT")}
              disabled={loading}
              className="text-xs bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              Marquer envoyé
            </button>
          )}
          {application.status === "SENT" && (
            <FollowupSection
              applicationId={application.id}
              onUpdate={onUpdate}
            />
          )}
          {application.status === "FOLLOW_UP_DUE" && (
            <div className="flex gap-1.5">
              <button
                onClick={() => transition("INTERVIEW")}
                disabled={loading}
                className="text-xs bg-purple-600 text-white px-2 py-1 rounded hover:bg-purple-700 disabled:opacity-50"
              >
                Entretien obtenu
              </button>
              <button
                onClick={() => transition("REJECTED")}
                disabled={loading}
                className="text-xs bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600 disabled:opacity-50"
              >
                Refusé
              </button>
            </div>
          )}
          {application.status === "INTERVIEW" && (
            <div className="flex gap-1.5">
              <button
                onClick={() => transition("ACCEPTED")}
                disabled={loading}
                className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700 disabled:opacity-50"
              >
                Accepté
              </button>
              <button
                onClick={() => transition("REJECTED")}
                disabled={loading}
                className="text-xs bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600 disabled:opacity-50"
              >
                Refusé
              </button>
            </div>
          )}
          {/* Archiver toujours disponible (ANY → ARCHIVED) */}
          <button
            onClick={() => transition("ARCHIVED")}
            disabled={loading}
            className="text-xs text-gray-400 hover:text-gray-600 hover:underline text-left"
          >
            Archiver
          </button>
        </div>
      )}

      {/* Timeline Sprint 9 */}
      <div className="mt-3 border-t border-gray-100 pt-2">
        <button
          onClick={() => setShowTimeline(!showTimeline)}
          className="text-xs text-gray-400 hover:text-blue-600 hover:underline"
        >
          {showTimeline ? "Masquer timeline" : "Voir timeline"}
        </button>
        {showTimeline && (
          <ApplicationTimeline
            applicationId={application.id}
            onReplyAdded={onUpdate}
          />
        )}
      </div>
    </div>
  );
}
