import Link from "next/link";
import { getOffers, getSources } from "@/lib/api";
import OfferCard from "@/components/OfferCard";
import FilterBar from "@/components/FilterBar";
import type { OfferState, WorkMode, SortBy, UserStatusValue } from "@/types/offer";

interface SearchParams {
  page?: string;
  state?: string;
  is_active?: string;
  contract_type?: string;
  work_mode?: string;
  source_id?: string;
  sort_by?: string;
  user_status?: string;
}

const STATE_FILTER_OPTIONS: { value: OfferState | ""; label: string }[] = [
  { value: "", label: "Tous les états" },
  { value: "DETECTED", label: "Détectées" },
  { value: "NORMALIZED", label: "Normalisées" },
  { value: "ANALYZED", label: "Analysées" },
  { value: "QUALIFIED", label: "Qualifiées" },
  { value: "DRAFT_PREPARED", label: "Brouillon prêt" },
  { value: "READY_FOR_REVIEW", label: "À valider" },
  { value: "SUBMITTED", label: "Soumises" },
  { value: "REJECTED", label: "Rejetées" },
  { value: "CLOSED", label: "Clôturées" },
];

export default async function OffersPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const page = parseInt(searchParams.page ?? "1", 10);
  const state = (searchParams.state as OfferState) || undefined;
  const is_active = searchParams.is_active !== "false";
  const contract_type = searchParams.contract_type || undefined;
  const work_mode = (searchParams.work_mode as WorkMode) || undefined;
  const source_id = searchParams.source_id || undefined;
  const sort_by = (searchParams.sort_by as SortBy) || "created_at";
  const user_status = (searchParams.user_status as UserStatusValue) || undefined;

  let data;
  let error: string | null = null;
  let sources = [];

  try {
    [data, sources] = await Promise.all([
      getOffers({
        page,
        page_size: 20,
        state,
        is_active,
        contract_type,
        work_mode,
        source_id,
        user_status,
        sort_by,
      }),
      getSources().catch(() => []),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Erreur inconnue";
  }

  // Paramètres courants pour le FilterBar (client component)
  const currentParams: Record<string, string> = {};
  if (searchParams.state) currentParams.state = searchParams.state;
  if (searchParams.contract_type) currentParams.contract_type = searchParams.contract_type;
  if (searchParams.work_mode) currentParams.work_mode = searchParams.work_mode;
  if (searchParams.source_id) currentParams.source_id = searchParams.source_id;
  if (searchParams.sort_by) currentParams.sort_by = searchParams.sort_by;
  if (searchParams.is_active) currentParams.is_active = searchParams.is_active;
  if (searchParams.user_status) currentParams.user_status = searchParams.user_status;

  // Liens pagination — préserve tous les filtres actifs
  const paginationParams = new URLSearchParams(currentParams);
  const prevHref = (() => {
    const p = new URLSearchParams(paginationParams);
    p.set("page", String(page - 1));
    return `/offers?${p.toString()}`;
  })();
  const nextHref = (() => {
    const p = new URLSearchParams(paginationParams);
    p.set("page", String(page + 1));
    return `/offers?${p.toString()}`;
  })();

  return (
    <div className="space-y-5">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Offres de stage</h1>
          {data && (
            <p className="text-sm text-gray-500 mt-0.5">
              {data.total} offre{data.total !== 1 ? "s" : ""} trouvée
              {data.total !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>

      {/* Filtres par état (pills) */}
      <div className="flex flex-wrap gap-2">
        {STATE_FILTER_OPTIONS.map((opt) => {
          const isActive = (state ?? "") === opt.value;
          const params = new URLSearchParams(currentParams);
          if (opt.value) {
            params.set("state", opt.value);
          } else {
            params.delete("state");
          }
          params.delete("page");
          return (
            <Link
              key={opt.value}
              href={`/offers?${params.toString()}`}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-blue-400 hover:text-blue-700"
              }`}
            >
              {opt.label}
            </Link>
          );
        })}
      </div>

      {/* Filtres avancés + tri (client component) */}
      <FilterBar currentParams={currentParams} sources={sources} />

      {/* Erreur */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700 font-medium">Erreur de chargement</p>
          <p className="text-xs text-red-500 mt-1">{error}</p>
          <Link
            href="/offers"
            className="text-xs text-red-700 underline mt-2 inline-block"
          >
            Réessayer
          </Link>
        </div>
      )}

      {/* État vide */}
      {!error && data && data.items.length === 0 && (
        <div className="bg-white border border-dashed border-gray-300 rounded-lg p-12 text-center">
          <p className="text-gray-500 font-medium">Aucune offre trouvée</p>
          <p className="text-sm text-gray-400 mt-1">
            {state || contract_type || work_mode
              ? "Aucune offre ne correspond aux filtres actifs."
              : "Aucune offre en base. Lancez le script de seed."}
          </p>
          <Link
            href="/offers"
            className="text-sm text-blue-600 hover:underline mt-3 inline-block"
          >
            Réinitialiser les filtres
          </Link>
        </div>
      )}

      {/* Grille des offres */}
      {!error && data && data.items.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.items.map((offer) => (
            <OfferCard key={offer.id} offer={offer} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && (data.page > 1 || data.has_next) && (
        <div className="flex items-center justify-center gap-4 pt-4">
          {data.page > 1 && (
            <Link
              href={prevHref}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50 text-gray-700"
            >
              ← Précédent
            </Link>
          )}
          <span className="text-sm text-gray-500">
            Page {data.page} sur {Math.ceil(data.total / data.page_size)}
          </span>
          {data.has_next && (
            <Link
              href={nextHref}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg bg-white hover:bg-gray-50 text-gray-700"
            >
              Suivant →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
