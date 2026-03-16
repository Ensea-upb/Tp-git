export interface UserPreferences {
  id: string;
  preferred_contract_types: string[] | null;
  preferred_work_modes: string[] | null;
  preferred_locations: string[] | null;
  preferred_keywords: string[] | null;
  preferred_domains: string[] | null;
  exclude_keywords: string[] | null;
  minimum_duration_months: number | null;
  created_at: string;
  updated_at: string;
}

export interface PreferencesUpdate {
  preferred_contract_types?: string[] | null;
  preferred_work_modes?: string[] | null;
  preferred_locations?: string[] | null;
  preferred_keywords?: string[] | null;
  preferred_domains?: string[] | null;
  exclude_keywords?: string[] | null;
  minimum_duration_months?: number | null;
}
