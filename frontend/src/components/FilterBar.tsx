"use client";

import { useRouter, usePathname } from "next/navigation";
import { useState } from "react";
import {
  CONTRACT_TYPE_OPTIONS,
  WORK_MODE_OPTIONS,
  SORT_OPTIONS,
  USER_STATUS_FILTER_OPTIONS,
} from "@/lib/constants";
import type { SourceOut } from "@/types/offer";

interface FilterBarProps {
  currentParams: Record<string, string>;
  sources: SourceOut[];
}

export default function FilterBar({ currentParams, sources }: FilterBarProps) {
  const router = useRouter();
  const [cityInput, setCityInput] = useState(currentParams.city ?? "");

  const handleChange = (key: string, value: string) => {
    const params = new URLSearchParams(currentParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.delete("page");
    router.push(`/offers?${params.toString()}`);
  };

  const handleCitySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleChange("city", cityInput.trim());
  };

  const selectClass =
    "text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200";
  const inputClass =
    "text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 w-32";

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Ville */}
      <form onSubmit={handleCitySubmit} className="flex items-center gap-1">
        <input
          type="text"
          className={inputClass}
          placeholder="Ville…"
          value={cityInput}
          onChange={(e) => setCityInput(e.target.value)}
          aria-label="Filtrer par ville"
        />
        {cityInput && (
          <button
            type="button"
            className="text-xs text-gray-400 hover:text-gray-600"
            onClick={() => { setCityInput(""); handleChange("city", ""); }}
            aria-label="Effacer filtre ville"
          >
            ✕
          </button>
        )}
      </form>

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

      {/* Statut utilisateur */}
      <select
        className={selectClass}
        value={currentParams.user_status ?? ""}
        onChange={(e) => handleChange("user_status", e.target.value)}
        aria-label="Filtrer par statut"
      >
        {USER_STATUS_FILTER_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Source (par type) */}
      <select
        className={selectClass}
        value={currentParams.source ?? ""}
        onChange={(e) => handleChange("source", e.target.value)}
        aria-label="Filtrer par source"
      >
        <option value="">Toutes les sources</option>
        <option value="wttj">Welcome to the Jungle</option>
        <option value="apec">APEC</option>
        <option value="indeed">Indeed</option>
        {sources
          .filter((s) => !["wttj", "apec", "indeed"].includes(s.source_type))
          .map((s) => (
            <option key={s.id} value={s.source_type}>
              {s.name}
            </option>
          ))}
      </select>

      {/* Score minimum */}
      <select
        className={selectClass}
        value={currentParams.score_min ?? ""}
        onChange={(e) => handleChange("score_min", e.target.value)}
        aria-label="Score minimum"
      >
        <option value="">Tous les scores</option>
        <option value="25">≥ 25</option>
        <option value="50">≥ 50</option>
        <option value="70">≥ 70</option>
        <option value="85">≥ 85</option>
      </select>

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
