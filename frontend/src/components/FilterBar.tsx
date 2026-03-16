"use client";

import { useRouter } from "next/navigation";
import {
  CONTRACT_TYPE_OPTIONS,
  WORK_MODE_OPTIONS,
  SORT_OPTIONS,
} from "@/lib/constants";
import type { SourceOut } from "@/types/offer";

interface FilterBarProps {
  currentParams: Record<string, string>;
  sources: SourceOut[];
}

export default function FilterBar({ currentParams, sources }: FilterBarProps) {
  const router = useRouter();

  const handleChange = (key: string, value: string) => {
    const params = new URLSearchParams(currentParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    // Réinitialiser la pagination sur tout changement de filtre
    params.delete("page");
    router.push(`/offers?${params.toString()}`);
  };

  const selectClass =
    "text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200";

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Contrat */}
      <select
        className={selectClass}
        value={currentParams.contract_type ?? ""}
        onChange={(e) => handleChange("contract_type", e.target.value)}
        aria-label="Filtrer par type de contrat"
      >
        {CONTRACT_TYPE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Mode de travail */}
      <select
        className={selectClass}
        value={currentParams.work_mode ?? ""}
        onChange={(e) => handleChange("work_mode", e.target.value)}
        aria-label="Filtrer par mode de travail"
      >
        {WORK_MODE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Source */}
      {sources.length > 0 && (
        <select
          className={selectClass}
          value={currentParams.source_id ?? ""}
          onChange={(e) => handleChange("source_id", e.target.value)}
          aria-label="Filtrer par source"
        >
          <option value="">Toutes les sources</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      )}

      {/* Tri */}
      <div className="ml-auto flex items-center gap-1.5">
        <span className="text-xs text-gray-400">Trier par</span>
        <select
          className={selectClass}
          value={currentParams.sort_by ?? "created_at"}
          onChange={(e) => handleChange("sort_by", e.target.value)}
          aria-label="Trier les offres"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
