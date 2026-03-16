"use client";

import Link from "next/link";
import type { Application } from "@/types/application";
import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_COLORS,
} from "@/types/application";
import { updateApplicationStatus, addFollowup } from "@/lib/api";
import { useState } from "react";

interface Props {
  application: Application;
  onUpdate: () => void;
}

export default function ApplicationCard({ application, onUpdate }: Props) {
  const [loading, setLoading] = useState(false);
  const [showDraft, setShowDraft] = useState(false);

  const statusLabel = APPLICATION_STATUS_LABELS[application.status];
  const statusColor = APPLICATION_STATUS_COLORS[application.status];

  async function markAsSent() {
    setLoading(true);
    try {
      await updateApplicationStatus(application.id, "SENT");
      onUpdate();
    } finally {
      setLoading(false);
    }
  }

  async function markAsInterview() {
    setLoading(true);
    try {
      await updateApplicationStatus(application.id, "INTERVIEW");
      onUpdate();
    } finally {
      setLoading(false);
    }
  }

  async function scheduleFollowup() {
    // Default: +7 days
    const date = new Date();
    date.setDate(date.getDate() + 7);
    setLoading(true);
    try {
      await addFollowup(application.id, {
        scheduled_at: date.toISOString(),
        notes: "Relance automatique",
      });
      onUpdate();
    } finally {
      setLoading(false);
    }
  }

  const hasDrafts = application.draft_cover_letter || application.draft_email;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* En-tête */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <Link
          href={`/offers/${application.offer_id}`}
          className="text-sm font-semibold text-gray-800 hover:text-blue-700 leading-tight"
        >
          Offre #{application.offer_id.slice(0, 8)}…
        </Link>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${statusColor}`}>
          {statusLabel}
        </span>
      </div>

      {/* Canal & notes */}
      {application.source_channel && (
        <p className="text-xs text-gray-500 mb-1">
          via <span className="font-medium">{application.source_channel}</span>
        </p>
      )}
      {application.notes && (
        <p className="text-xs text-gray-500 mb-2 line-clamp-2">{application.notes}</p>
      )}

      {/* Date de candidature */}
      {application.applied_at && (
        <p className="text-xs text-gray-400 mb-2">
          Envoyé le{" "}
          {new Date(application.applied_at).toLocaleDateString("fr-FR")}
        </p>
      )}

      {/* Relances */}
      {application.followups.length > 0 && (
        <p className="text-xs text-orange-600 mb-2">
          {application.followups.length} relance(s) planifiée(s)
        </p>
      )}

      {/* Brouillons LLM */}
      {hasDrafts && (
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
      )}

      {/* Actions contextuelles */}
      <div className="flex flex-wrap gap-1.5 mt-2">
        {(application.status === "DRAFT" || application.status === "READY_TO_SEND") && (
          <button
            onClick={markAsSent}
            disabled={loading}
            className="text-xs bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            Marquer envoyé
          </button>
        )}
        {application.status === "SENT" && (
          <>
            <button
              onClick={scheduleFollowup}
              disabled={loading}
              className="text-xs bg-orange-500 text-white px-2 py-1 rounded hover:bg-orange-600 disabled:opacity-50"
            >
              + Relance
            </button>
            <button
              onClick={markAsInterview}
              disabled={loading}
              className="text-xs bg-purple-600 text-white px-2 py-1 rounded hover:bg-purple-700 disabled:opacity-50"
            >
              Entretien
            </button>
          </>
        )}
        {application.status === "FOLLOW_UP_DUE" && (
          <button
            onClick={markAsInterview}
            disabled={loading}
            className="text-xs bg-purple-600 text-white px-2 py-1 rounded hover:bg-purple-700 disabled:opacity-50"
          >
            Entretien obtenu
          </button>
        )}
      </div>
    </div>
  );
}
