"use client";

import { useCallback, useEffect, useState } from "react";
import { getApplications } from "@/lib/api";
import type { Application, ApplicationStatus } from "@/types/application";
import { APPLICATION_STATUS_LABELS } from "@/types/application";
import ApplicationCard from "@/components/ApplicationCard";
import ApplicationPipeline from "@/components/ApplicationPipeline";

const FILTER_OPTIONS: { label: string; value: ApplicationStatus | "" }[] = [
  { label: "Tous", value: "" },
  { label: "Brouillon", value: "DRAFT" },
  { label: "Prêt à envoyer", value: "READY_TO_SEND" },
  { label: "Envoyé", value: "SENT" },
  { label: "Relance", value: "FOLLOW_UP_DUE" },
  { label: "Entretien", value: "INTERVIEW" },
  { label: "Accepté", value: "ACCEPTED" },
  { label: "Refusé", value: "REJECTED" },
  { label: "Archivé", value: "ARCHIVED" },
];

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const limit = 50;

  const loadApplications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getApplications({
        status: statusFilter || undefined,
        page,
        limit,
      });
      setApplications(data.items);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    loadApplications();
  }, [loadApplications]);

  // Reset page when filter changes
  function handleFilterChange(value: ApplicationStatus | "") {
    setPage(1);
    setStatusFilter(value);
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Candidatures</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} candidature{total !== 1 ? "s" : ""}
            {statusFilter ? ` · filtrées : ${APPLICATION_STATUS_LABELS[statusFilter]}` : ""}
          </p>
        </div>
        <a
          href="/offers"
          className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Depuis une offre
        </a>
      </div>

      {/* Filtre par statut */}
      <div className="flex flex-wrap gap-2 mb-6">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handleFilterChange(opt.value as ApplicationStatus | "")}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              statusFilter === opt.value
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Chargement */}
      {loading && (
        <div className="flex justify-center py-16">
          <div className="text-sm text-gray-400">Chargement du pipeline…</div>
        </div>
      )}

      {/* Erreur */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-600">{error}</p>
          <button
            onClick={loadApplications}
            className="text-xs text-red-500 hover:underline mt-1"
          >
            Réessayer
          </button>
        </div>
      )}

      {/* Pipeline Kanban (masqué si filtre actif → liste plate plus lisible) */}
      {!loading && !error && !statusFilter && (
        <ApplicationPipeline applications={applications} onUpdate={loadApplications} />
      )}

      {/* Vue liste si filtre statut actif */}
      {!loading && !error && statusFilter && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {applications.length === 0 ? (
            <p className="col-span-full text-sm text-gray-400 text-center py-12">
              Aucune candidature dans cet état.
            </p>
          ) : (
            applications.map((app) => (
              <ApplicationCard key={app.id} application={app} onUpdate={loadApplications} />
            ))
          )}
        </div>
      )}

      {/* Pagination (affiché si filtre actif et résultats > limit) */}
      {!loading && !error && statusFilter && total > limit && (
        <div className="flex justify-center gap-3 mt-6">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="text-sm px-4 py-2 border rounded disabled:opacity-40"
          >
            ← Précédent
          </button>
          <span className="text-sm text-gray-500 self-center">
            Page {page} / {Math.ceil(total / limit)}
          </span>
          <button
            disabled={page * limit >= total}
            onClick={() => setPage((p) => p + 1)}
            className="text-sm px-4 py-2 border rounded disabled:opacity-40"
          >
            Suivant →
          </button>
        </div>
      )}
    </div>
  );
}
