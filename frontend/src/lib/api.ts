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
import type {
  OfferLLMAnalysis,
  ProfileMatch,
  CandidateProfile,
  CandidateProfileUpdate,
  AssistantResult,
} from "@/types/analysis";
import type {
  Application,
  ApplicationCreate,
  ApplicationEvent,
  ApplicationStats,
  ApplicationStatus,
  FollowupCreate,
  FollowupRecommendation,
  Followup,
  PaginatedApplications,
  RecruiterReplyCreate,
} from "@/types/application";

// SSR (server components inside Docker) → use internal service name
// CSR (browser) → use public URL exposed on localhost
const API_BASE_URL =
  typeof window === "undefined"
    ? (process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

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
  source?: string;
  city?: string;
  score_min?: number;
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
  if (params?.source) searchParams.set("source", params.source);
  if (params?.city) searchParams.set("city", params.city);
  if (params?.score_min !== undefined) searchParams.set("score_min", String(params.score_min));
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

// ── LLM Analysis ─────────────────────────────────────────────────────

export async function triggerOfferAnalysis(offerId: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/offers/${offerId}/analyze`, { method: "POST" });
}

export async function getOfferAnalysis(offerId: string): Promise<OfferLLMAnalysis> {
  return apiFetch<OfferLLMAnalysis>(`/offers/${offerId}/analysis`);
}

export async function triggerProfileMatch(offerId: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/offers/${offerId}/match-profile`, { method: "POST" });
}

export async function getProfileMatch(offerId: string): Promise<ProfileMatch> {
  return apiFetch<ProfileMatch>(`/offers/${offerId}/match`);
}

// ── Application Assistant ────────────────────────────────────────────

export async function generateCoverLetter(offerId: string): Promise<AssistantResult> {
  return apiFetch<AssistantResult>(`/offers/${offerId}/cover-letter`, { method: "POST" });
}

export async function generateApplicationEmail(offerId: string): Promise<AssistantResult> {
  return apiFetch<AssistantResult>(`/offers/${offerId}/email`, { method: "POST" });
}

export async function generateInterviewPrep(offerId: string): Promise<AssistantResult> {
  return apiFetch<AssistantResult>(`/offers/${offerId}/interview-prep`, { method: "POST" });
}

// ── Candidate Profile ────────────────────────────────────────────────

export async function getCandidateProfile(): Promise<CandidateProfile> {
  return apiFetch<CandidateProfile>("/candidate");
}

export async function updateCandidateProfile(
  body: CandidateProfileUpdate
): Promise<CandidateProfile> {
  return apiFetch<CandidateProfile>("/candidate", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

// ── Applications ──────────────────────────────────────────────────────

export async function createApplication(body: ApplicationCreate): Promise<Application> {
  return apiFetch<Application>("/applications", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getApplications(params?: {
  status?: ApplicationStatus;
  page?: number;
  limit?: number;
}): Promise<PaginatedApplications> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.page) sp.set("page", String(params.page));
  if (params?.limit) sp.set("limit", String(params.limit));
  const query = sp.toString() ? `?${sp.toString()}` : "";
  return apiFetch<PaginatedApplications>(`/applications${query}`);
}

export async function getApplication(id: string): Promise<Application> {
  return apiFetch<Application>(`/applications/${id}`);
}

export async function updateApplicationStatus(
  id: string,
  status: ApplicationStatus
): Promise<Application> {
  return apiFetch<Application>(`/applications/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function addFollowup(id: string, body: FollowupCreate): Promise<Followup> {
  return apiFetch<Followup>(`/applications/${id}/followup`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Sprint 9 ──────────────────────────────────────────────────────────────────

export async function getApplicationTimeline(id: string): Promise<ApplicationEvent[]> {
  return apiFetch<ApplicationEvent[]>(`/applications/${id}/timeline`);
}

export async function addRecruiterReply(
  id: string,
  body: RecruiterReplyCreate
): Promise<ApplicationEvent> {
  return apiFetch<ApplicationEvent>(`/applications/${id}/recruiter-reply`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getFollowupRecommendation(
  id: string
): Promise<FollowupRecommendation> {
  return apiFetch<FollowupRecommendation>(`/applications/${id}/followup-recommendation`);
}

export async function getApplicationStats(): Promise<ApplicationStats> {
  return apiFetch<ApplicationStats>("/applications/stats");
}

export async function getContextualInterviewPrep(id: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/applications/${id}/interview-prep`, {
    method: "POST",
  });
}

// ── Sprint 10 : Strategy ──────────────────────────────────────────────────────

import type { StrategyRecommendations, PrioritizedOffer } from "@/types/strategy";

export async function getStrategyRecommendations(
  limit = 10
): Promise<StrategyRecommendations> {
  return apiFetch<StrategyRecommendations>(`/strategy/recommendations?limit=${limit}`);
}

export async function getPrioritizedOffers(limit = 10): Promise<PrioritizedOffer[]> {
  return apiFetch<PrioritizedOffer[]>(`/offers/prioritized?limit=${limit}`);
}
