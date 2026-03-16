import type {
  OfferDetail,
  PaginatedOffers,
  OfferState,
  WorkMode,
  SortBy,
  SourceOut,
  UserStatusValue,
} from "@/types/offer";
import type { UserPreferences, PreferencesUpdate } from "@/types/preferences";

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
    cache: process.env.NODE_ENV === "development" ? "no-store" : "default",
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  // 204 No Content
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

// ── Offers ──────────────────────────────────────────────────────────

export async function getOffers(params?: {
  page?: number;
  page_size?: number;
  state?: OfferState;
  is_active?: boolean;
  contract_type?: string;
  work_mode?: WorkMode;
  source_id?: string;
  user_status?: UserStatusValue;
  sort_by?: SortBy;
}): Promise<PaginatedOffers> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.state) searchParams.set("state", params.state);
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
  if (params?.contract_type) searchParams.set("contract_type", params.contract_type);
  if (params?.work_mode) searchParams.set("work_mode", params.work_mode);
  if (params?.source_id) searchParams.set("source_id", params.source_id);
  if (params?.user_status) searchParams.set("user_status", params.user_status);
  if (params?.sort_by) searchParams.set("sort_by", params.sort_by);

  const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
  return apiFetch<PaginatedOffers>(`/offers${query}`);
}

export async function getOffer(id: string): Promise<OfferDetail> {
  return apiFetch<OfferDetail>(`/offers/${id}`);
}

// ── Sources ─────────────────────────────────────────────────────────

export async function getSources(): Promise<SourceOut[]> {
  return apiFetch<SourceOut[]>("/sources");
}

// ── Preferences ──────────────────────────────────────────────────────

export async function getPreferences(): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/preferences");
}

export async function updatePreferences(body: PreferencesUpdate): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/preferences", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

// ── Offer actions ────────────────────────────────────────────────────

type ActionType = "favorite" | "shortlist" | "reject";

export async function setOfferAction(offerId: string, action: ActionType): Promise<void> {
  await apiFetch<void>(`/offers/${offerId}/${action}`, { method: "POST" });
}

export async function removeOfferAction(offerId: string, action: ActionType): Promise<void> {
  await apiFetch<void>(`/offers/${offerId}/${action}`, { method: "DELETE" });
}
