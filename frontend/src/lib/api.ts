import type { OfferDetail, PaginatedOffers } from "@/types/offer";
import type { OfferState } from "@/types/offer";

// L'URL de l'API est lue depuis les variables d'environnement Next.js
// Côté serveur (Server Components) : utilise l'URL interne Docker
// La clé API est stockée côté serveur uniquement
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.INTERNAL_API_KEY || "dev-api-key-changeme";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}/v1${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
      ...(options?.headers ?? {}),
    },
    // Pas de cache en développement pour toujours avoir les données fraîches
    cache: process.env.NODE_ENV === "development" ? "no-store" : "default",
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json() as Promise<T>;
}

export async function getOffers(params?: {
  page?: number;
  page_size?: number;
  state?: OfferState;
  is_active?: boolean;
}): Promise<PaginatedOffers> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.state) searchParams.set("state", params.state);
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));

  const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return apiFetch<PaginatedOffers>(`/offers${query}`);
}

export async function getOffer(id: string): Promise<OfferDetail> {
  return apiFetch<OfferDetail>(`/offers/${id}`);
}
