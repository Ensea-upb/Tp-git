import Link from "next/link";
import { getOffers } from "@/lib/api";

export default async function HomePage() {
  let stats = { total: 0, qualified: 0, ready_for_review: 0 };

  try {
    const [all, qualified, readyForReview] = await Promise.all([
      getOffers({ is_active: true, page_size: 1 }),
      getOffers({ state: "QUALIFIED", is_active: true, page_size: 1 }),
      getOffers({ state: "READY_FOR_REVIEW", is_active: true, page_size: 1 }),
    ]);
    stats = {
      total: all.total,
      qualified: qualified.total,
      ready_for_review: readyForReview.total,
    };
  } catch {
    // Backend non disponible — afficher des données vides
  }

  const indicators = [
    {
      label: "Offres actives",
      value: stats.total,
      description: "Offres détectées et actives",
      href: "/offers",
      color: "border-blue-500",
    },
    {
      label: "Offres qualifiées",
      value: stats.qualified,
      description: "Prêtes pour candidature",
      href: "/offers?state=QUALIFIED",
      color: "border-green-500",
    },
    {
      label: "À valider",
      value: stats.ready_for_review,
      description: "Brouillons en attente",
      href: "/offers?state=READY_FOR_REVIEW",
      color: stats.ready_for_review > 0 ? "border-orange-500" : "border-gray-200",
    },
  ];

  return (
    <div className="space-y-8">
      {/* En-tête */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Copilote intelligent de recherche de stage — Sprint 1
        </p>
      </div>

      {/* Indicateurs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {indicators.map((ind) => (
          <Link key={ind.label} href={ind.href}>
            <div className={`bg-white rounded-lg border-l-4 ${ind.color} border border-gray-200 p-5 hover:shadow-md transition-shadow`}>
              <p className="text-sm font-medium text-gray-500">{ind.label}</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{ind.value}</p>
              <p className="text-xs text-gray-400 mt-1">{ind.description}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* Accès rapide */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-base font-semibold text-gray-800 mb-4">Accès rapide</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Link
            href="/offers"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-all"
          >
            <span className="text-2xl">📋</span>
            <div>
              <p className="text-sm font-medium text-gray-800">Consulter les offres</p>
              <p className="text-xs text-gray-500">Liste et détail des offres détectées</p>
            </div>
          </Link>
          <div className="flex items-center gap-3 p-4 rounded-lg border border-dashed border-gray-200 opacity-50 cursor-not-allowed">
            <span className="text-2xl">✉️</span>
            <div>
              <p className="text-sm font-medium text-gray-600">Candidatures</p>
              <p className="text-xs text-gray-400">Disponible Sprint 4</p>
            </div>
          </div>
        </div>
      </div>

      {/* Roadmap Sprint */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-base font-semibold text-gray-800 mb-4">Roadmap</h2>
        <div className="space-y-2">
          {[
            { sprint: "Sprint 1", label: "Socle technique + offres fictives", done: true },
            { sprint: "Sprint 2", label: "Ingestion réelle (pages carrières + France Travail API)", done: false },
            { sprint: "Sprint 3", label: "Scoring LLM + qualification", done: false },
            { sprint: "Sprint 4", label: "Génération brouillons de candidature", done: false },
            { sprint: "Sprint 5", label: "Validation humaine + soumission", done: false },
            { sprint: "Sprint 6", label: "Suivi candidatures + relances", done: false },
          ].map((item) => (
            <div key={item.sprint} className="flex items-center gap-3">
              <span className={`w-4 h-4 rounded-full flex-shrink-0 ${item.done ? "bg-green-500" : "bg-gray-200"}`} />
              <span className="text-xs font-medium text-gray-500 w-16 flex-shrink-0">{item.sprint}</span>
              <span className={`text-sm ${item.done ? "text-gray-800" : "text-gray-400"}`}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
