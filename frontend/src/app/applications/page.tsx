"use client";

import { useEffect, useState, useCallback } from "react";
import { getApplications } from "@/lib/api";
import type { Application } from "@/types/application";
import ApplicationPipeline from "@/components/ApplicationPipeline";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadApplications = useCallback(async () => {
    try {
      const data = await getApplications();
      setApplications(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadApplications();
  }, [loadApplications]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Candidatures</h1>
          <p className="text-sm text-gray-500 mt-1">
            {applications.length} candidature{applications.length !== 1 ? "s" : ""} en cours
          </p>
        </div>
        <a
          href="/offers"
          className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Nouvelle depuis une offre
        </a>
      </div>

      {/* Statut */}
      {loading && (
        <div className="flex justify-center py-16">
          <div className="text-sm text-gray-400">Chargement du pipeline…</div>
        </div>
      )}

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

      {/* Pipeline Kanban */}
      {!loading && !error && (
        <ApplicationPipeline
          applications={applications}
          onUpdate={loadApplications}
        />
      )}
    </div>
  );
}
