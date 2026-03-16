"use client";

import { useEffect, useState } from "react";
import { getPreferences, updatePreferences } from "@/lib/api";
import type { UserPreferences, PreferencesUpdate } from "@/types/preferences";
import { DOMAIN_OPTIONS, WORK_MODE_OPTIONS, CONTRACT_TYPE_OPTIONS } from "@/lib/constants";
import Link from "next/link";

// ── Petit helper pour éditer une liste de strings ─────────────────

function TagListEditor({
  label,
  values,
  onChange,
  placeholder,
}: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");

  const add = () => {
    const trimmed = input.trim();
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed]);
    }
    setInput("");
  };

  const remove = (v: string) => onChange(values.filter((x) => x !== v));

  return (
    <div>
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex flex-wrap gap-1.5 mt-1.5 mb-2 min-h-8">
        {values.map((v) => (
          <span
            key={v}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-full text-xs font-medium"
          >
            {v}
            <button
              type="button"
              onClick={() => remove(v)}
              className="text-blue-400 hover:text-blue-700 leading-none"
            >
              ×
            </button>
          </span>
        ))}
        {values.length === 0 && (
          <span className="text-xs text-gray-400 italic">Aucun élément</span>
        )}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder={placeholder}
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
        />
        <button
          type="button"
          onClick={add}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Ajouter
        </button>
      </div>
    </div>
  );
}

function CheckboxGroup({
  label,
  options,
  values,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  values: string[];
  onChange: (v: string[]) => void;
}) {
  const toggle = (v: string) => {
    if (values.includes(v)) onChange(values.filter((x) => x !== v));
    else onChange([...values, v]);
  };

  return (
    <div>
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex flex-wrap gap-2 mt-2">
        {options
          .filter((o) => o.value !== "")
          .map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium border transition-colors ${
                values.includes(opt.value)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-blue-400"
              }`}
            >
              {opt.label}
            </button>
          ))}
      </div>
    </div>
  );
}

// ── Page principale ────────────────────────────────────────────────

export default function PreferencesPage() {
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Formulaire local
  const [contractTypes, setContractTypes] = useState<string[]>([]);
  const [workModes, setWorkModes] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [excludeKeywords, setExcludeKeywords] = useState<string[]>([]);
  const [minDuration, setMinDuration] = useState<string>("");

  useEffect(() => {
    getPreferences()
      .then((data) => {
        setPrefs(data);
        setContractTypes(data.preferred_contract_types ?? []);
        setWorkModes(data.preferred_work_modes ?? []);
        setLocations(data.preferred_locations ?? []);
        setKeywords(data.preferred_keywords ?? []);
        setDomains(data.preferred_domains ?? []);
        setExcludeKeywords(data.exclude_keywords ?? []);
        setMinDuration(data.minimum_duration_months?.toString() ?? "");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const body: PreferencesUpdate = {
        preferred_contract_types: contractTypes.length ? contractTypes : null,
        preferred_work_modes: workModes.length ? workModes : null,
        preferred_locations: locations.length ? locations : null,
        preferred_keywords: keywords.length ? keywords : null,
        preferred_domains: domains.length ? domains : null,
        exclude_keywords: excludeKeywords.length ? excludeKeywords : null,
        minimum_duration_months: minDuration ? parseInt(minDuration, 10) : null,
      };
      const updated = await updatePreferences(body);
      setPrefs(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl space-y-4">
        <div className="h-8 bg-gray-100 rounded w-48 animate-pulse" />
        <div className="h-64 bg-gray-100 rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Préférences de recherche</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Ces préférences sont utilisées pour calculer le score personnalisé de chaque offre.
          </p>
        </div>
        <Link href="/offers" className="text-sm text-gray-400 hover:text-blue-700">
          ← Offres
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
        {/* Contrats */}
        <div className="p-5">
          <CheckboxGroup
            label="Types de contrat préférés"
            options={CONTRACT_TYPE_OPTIONS}
            values={contractTypes}
            onChange={setContractTypes}
          />
        </div>

        {/* Mode de travail */}
        <div className="p-5">
          <CheckboxGroup
            label="Modes de travail préférés"
            options={WORK_MODE_OPTIONS}
            values={workModes}
            onChange={setWorkModes}
          />
        </div>

        {/* Domaines */}
        <div className="p-5">
          <CheckboxGroup
            label="Domaines préférés"
            options={DOMAIN_OPTIONS}
            values={domains}
            onChange={setDomains}
          />
        </div>

        {/* Localisations */}
        <div className="p-5">
          <TagListEditor
            label="Localisations préférées"
            values={locations}
            onChange={setLocations}
            placeholder="ex : Paris, Lyon, Île-de-France"
          />
        </div>

        {/* Mots-clés positifs */}
        <div className="p-5">
          <TagListEditor
            label="Mots-clés recherchés"
            values={keywords}
            onChange={setKeywords}
            placeholder="ex : python, fastapi, postgresql"
          />
        </div>

        {/* Mots-clés exclus */}
        <div className="p-5">
          <TagListEditor
            label="Mots-clés à exclure"
            values={excludeKeywords}
            onChange={setExcludeKeywords}
            placeholder="ex : COBOL, PHP legacy"
          />
        </div>

        {/* Durée minimale */}
        <div className="p-5">
          <label className="text-sm font-medium text-gray-700">Durée minimale (mois)</label>
          <input
            type="number"
            min={1}
            max={24}
            value={minDuration}
            onChange={(e) => setMinDuration(e.target.value)}
            placeholder="ex : 4"
            className="mt-1.5 w-32 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
          />
        </div>
      </div>

      {/* Bouton sauvegarde */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "Enregistrement…" : "Enregistrer les préférences"}
        </button>
        {saved && (
          <span className="text-sm text-green-600 font-medium">
            ✓ Préférences enregistrées
          </span>
        )}
      </div>

      <p className="text-xs text-gray-400">
        Après modification, relancez un rescore via{" "}
        <code className="bg-gray-100 px-1 rounded">python scripts/rescore_offers.py</code>{" "}
        pour recalculer les scores personnalisés sur les offres existantes.
      </p>
    </div>
  );
}
