"use client";

import { useEffect, useState } from "react";
import { getApplicationTimeline, addRecruiterReply } from "@/lib/api";
import type { ApplicationEvent } from "@/types/application";

const EVENT_ICONS: Record<string, string> = {
  APPLICATION_CREATED: "📝",
  STATUS_CHANGED: "🔄",
  FOLLOWUP_SCHEDULED: "📅",
  RECRUITER_REPLIED: "💬",
  DRAFTS_READY: "✉️",
};

const EVENT_LABELS: Record<string, string> = {
  APPLICATION_CREATED: "Candidature créée",
  STATUS_CHANGED: "Changement de statut",
  FOLLOWUP_SCHEDULED: "Relance planifiée",
  RECRUITER_REPLIED: "Réponse recruteur",
  DRAFTS_READY: "Brouillons prêts",
};

function formatEventDetail(event: ApplicationEvent): string {
  const p = event.payload_json;
  if (!p) return "";
  if (event.event_type === "STATUS_CHANGED") {
    return `${p.from} → ${p.to}`;
  }
  if (event.event_type === "RECRUITER_REPLIED") {
    const msg = (p.message_text as string)?.slice(0, 80) ?? "";
    const channel = (p.channel as string) ?? "";
    return channel ? `[${channel}] ${msg}` : msg;
  }
  if (event.event_type === "FOLLOWUP_SCHEDULED") {
    const d = p.scheduled_at as string;
    return `Prévue le ${new Date(d).toLocaleDateString("fr-FR")}`;
  }
  return "";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface Props {
  applicationId: string;
  onReplyAdded?: () => void;
}

export default function ApplicationTimeline({ applicationId, onReplyAdded }: Props) {
  const [events, setEvents] = useState<ApplicationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [replyChannel, setReplyChannel] = useState("email");
  const [submitting, setSubmitting] = useState(false);

  async function loadTimeline() {
    setLoading(true);
    try {
      const data = await getApplicationTimeline(applicationId);
      setEvents(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTimeline();
  }, [applicationId]);

  async function handleReplySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!replyText.trim()) return;
    setSubmitting(true);
    try {
      await addRecruiterReply(applicationId, {
        message_text: replyText.trim(),
        channel: replyChannel,
      });
      setReplyText("");
      setShowReplyForm(false);
      await loadTimeline();
      onReplyAdded?.();
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <p className="text-xs text-gray-400 py-2">Chargement timeline…</p>;
  }

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">Timeline</h3>
        <button
          onClick={() => setShowReplyForm(!showReplyForm)}
          className="text-xs text-blue-600 hover:underline"
        >
          + Réponse recruteur
        </button>
      </div>

      {/* Formulaire réponse recruteur */}
      {showReplyForm && (
        <form
          onSubmit={handleReplySubmit}
          className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-2"
        >
          <div className="flex gap-2">
            <select
              value={replyChannel}
              onChange={(e) => setReplyChannel(e.target.value)}
              className="text-xs border rounded px-2 py-1 bg-white"
            >
              <option value="email">Email</option>
              <option value="phone">Téléphone</option>
              <option value="linkedin">LinkedIn</option>
              <option value="other">Autre</option>
            </select>
          </div>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Message du recruteur…"
            rows={2}
            className="w-full text-xs border rounded px-2 py-1 resize-none"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting || !replyText.trim()}
              className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-40"
            >
              Enregistrer
            </button>
            <button
              type="button"
              onClick={() => setShowReplyForm(false)}
              className="text-xs text-gray-500 hover:underline"
            >
              Annuler
            </button>
          </div>
        </form>
      )}

      {/* Liste des événements */}
      {events.length === 0 ? (
        <p className="text-xs text-gray-400">Aucun événement.</p>
      ) : (
        <ol className="relative border-l border-gray-200 ml-2 space-y-3">
          {events.map((event) => {
            const detail = formatEventDetail(event);
            return (
              <li key={event.id} className="ml-4">
                <span className="absolute -left-2 flex items-center justify-center w-4 h-4 text-xs">
                  {EVENT_ICONS[event.event_type] ?? "•"}
                </span>
                <div className="text-xs">
                  <span className="font-medium text-gray-700">
                    {EVENT_LABELS[event.event_type] ?? event.event_type}
                  </span>
                  {detail && (
                    <span className="text-gray-500 ml-1">— {detail}</span>
                  )}
                  <p className="text-gray-400 mt-0.5">{formatDate(event.created_at)}</p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
