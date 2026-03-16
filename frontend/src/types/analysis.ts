export interface OfferLLMAnalysis {
  offer_id: string;
  model_used: string;
  summary: string | null;
  missions: string[] | null;
  skills_required: string[] | null;
  tech_stack: string[] | null;
  seniority_level: string | null;
  analysis_status: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  analyzed_at: string;
  updated_at: string;
}

export interface ProfileMatch {
  offer_id: string;
  model_used: string;
  match_score: number | null;
  strengths: string[] | null;
  gaps: string[] | null;
  recommendation: string | null;
  match_status: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  matched_at: string;
  updated_at: string;
}

export interface CandidateProfile {
  id: string;
  full_name: string | null;
  current_level: string | null;
  school: string | null;
  summary: string | null;
  skills: string[] | null;
  tech_stack: string[] | null;
  languages: string[] | null;
  experiences: Array<{
    title: string;
    company: string;
    duration?: string;
    description?: string;
  }> | null;
  projects: Array<{
    name: string;
    description?: string;
    tech?: string[];
  }> | null;
  target_domains: string[] | null;
  availability: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateProfileUpdate {
  full_name?: string | null;
  current_level?: string | null;
  school?: string | null;
  summary?: string | null;
  skills?: string[] | null;
  tech_stack?: string[] | null;
  languages?: string[] | null;
  experiences?: CandidateProfile["experiences"];
  projects?: CandidateProfile["projects"];
  target_domains?: string[] | null;
  availability?: string | null;
}

export interface AssistantResult {
  subject?: string;
  body?: string;
  technical_questions?: string[];
  behavioral_questions?: string[];
  questions_to_ask?: string[];
  preparation_tips?: string[];
  error?: string;
}
