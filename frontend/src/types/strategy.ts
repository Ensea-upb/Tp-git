export type StrategyActionType =
  | "APPLY_NOW"
  | "SEND_FOLLOWUP"
  | "PREPARE_INTERVIEW"
  | "ARCHIVE_STALE";

export interface StrategyAction {
  action_type: StrategyActionType;
  reason: string;
  priority: number;
  application_id: string | null;
  offer_id: string | null;
}

export interface PrioritizedOffer {
  offer_id: string;
  title: string;
  priority_score: number;
  ranking_score: number | null;
  matching_score: number | null;
  location_text: string | null;
  company_name: string | null;
}

export interface SkillGap {
  offer_id: string;
  offer_title: string;
  missing_skills: string[];
}

export interface StrategyRecommendations {
  actions: StrategyAction[];
  prioritized_offers: PrioritizedOffer[];
  skill_gaps: SkillGap[];
}
