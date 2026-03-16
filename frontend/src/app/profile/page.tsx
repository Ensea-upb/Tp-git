"use client";

import { useState, useEffect } from "react";
import type { CandidateProfile, CandidateProfileUpdate } from "@/types/analysis";
import { getCandidateProfile, updateCandidateProfile } from "@/lib/api";

function TagListEditor({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");

  const add = () => {
    const trimmed = input.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
      setInput("");
    }
  };

  const remove = (item: string) => onChange(value.filter((v) => v !== item));

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <div className="flex gap-2 mb-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder={placeholder || "Ajouter…"}
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
        />
        <button
          type="button"
          onClick={add}
          className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100"
        >
          +
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {value.map((item) => (
          <span
            key={item}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-full"
          >
            {item}
            <button
              type="button"
              onClick={() => remove(item)}
              className="text-gray-400 hover:text-red-500"
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [form, setForm] = useState<CandidateProfileUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCandidateProfile()
      .then((p) => {
        setProfile(p);
        setForm({
          full_name: p.full_name ?? "",
          current_level: p.current_level ?? "",
          school: p.school ?? "",
          summary: p.summary ?? "",
          skills: p.skills ?? [],
          tech_stack: p.tech_stack ?? [],
          languages: p.languages ?? [],
          target_domains: p.target_domains ?? [],
          availability: p.availability ?? "",
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateCandidateProfile(form);
      setProfile(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setSaving(false);
    }
  };

  const set = (field: keyof CandidateProfileUpdate, value: unknown) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="text-sm text-gray-500 py-12 text-center">Chargement du profil…</div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Profil candidat</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Votre profil est utilisé par le copilote IA pour évaluer la compatibilité et générer les
          candidatures.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-5">
        {/* Identité */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom complet</label>
            <input
              type="text"
              value={form.full_name ?? ""}
              onChange={(e) => set("full_name", e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
              placeholder="Ex. Alice Martin"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Disponibilité</label>
            <input
              type="text"
              value={form.availability ?? ""}
              onChange={(e) => set("availability", e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
              placeholder="Ex. Avril 2026"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Niveau actuel</label>
            <input
              type="text"
              value={form.current_level ?? ""}
              onChange={(e) => set("current_level", e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
              placeholder="Ex. Master 2 Data Science"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">École</label>
            <input
              type="text"
              value={form.school ?? ""}
              onChange={(e) => set("school", e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400"
              placeholder="Ex. Paris Dauphine"
            />
          </div>
        </div>

        {/* Bio */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Présentation (bio)
          </label>
          <textarea
            value={form.summary ?? ""}
            onChange={(e) => set("summary", e.target.value)}
            rows={4}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400 resize-none"
            placeholder="Qui êtes-vous, votre parcours, vos centres d'intérêt…"
          />
        </div>

        {/* Compétences */}
        <TagListEditor
          label="Compétences"
          value={form.skills ?? []}
          onChange={(v) => set("skills", v)}
          placeholder="Machine Learning, SQL, etc."
        />

        <TagListEditor
          label="Stack technique"
          value={form.tech_stack ?? []}
          onChange={(v) => set("tech_stack", v)}
          placeholder="Python, PyTorch, etc."
        />

        <TagListEditor
          label="Langues"
          value={form.languages ?? []}
          onChange={(v) => set("languages", v)}
          placeholder="Français, Anglais, etc."
        />

        <TagListEditor
          label="Domaines cibles"
          value={form.target_domains ?? []}
          onChange={(v) => set("target_domains", v)}
          placeholder="data, ml, analytics, etc."
        />
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Enregistrement…" : "Enregistrer"}
        </button>
        {saved && (
          <span className="text-sm text-green-600 font-medium">Profil enregistré ✓</span>
        )}
      </div>
    </div>
  );
}
