export type ApplicationStatus =
  | "DRAFT"
  | "READY_TO_SEND"
  | "SENT"
  | "FOLLOW_UP_DUE"
  | "INTERVIEW"
  | "REJECTED"
  | "ACCEPTED"
  | "ARCHIVED";

export interface Followup {
  id: string;
  application_id: string;
  scheduled_at: string;
  sent_at: string | null;
  status: string;
  notes: string | null;
  created_at: string;
}

export interface Application {
  id: string;
  offer_id: string;
  status: ApplicationStatus;
  applied_at: string | null;
  source_channel: string | null;
  draft_cover_letter: string | null;
  draft_email: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  followups: Followup[];
}

export interface ApplicationCreate {
  offer_id: string;
  source_channel?: string;
  notes?: string;
}

export interface ApplicationStatusUpdate {
  status: ApplicationStatus;
}

export interface FollowupCreate {
  scheduled_at: string;
  notes?: string;
}

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  DRAFT: "Brouillon",
  READY_TO_SEND: "Prêt à envoyer",
  SENT: "Envoyé",
  FOLLOW_UP_DUE: "Relance à faire",
  INTERVIEW: "Entretien",
  REJECTED: "Refusé",
  ACCEPTED: "Accepté",
  ARCHIVED: "Archivé",
};

export const APPLICATION_STATUS_COLORS: Record<ApplicationStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  READY_TO_SEND: "bg-blue-100 text-blue-700",
  SENT: "bg-indigo-100 text-indigo-700",
  FOLLOW_UP_DUE: "bg-orange-100 text-orange-700",
  INTERVIEW: "bg-purple-100 text-purple-700",
  REJECTED: "bg-red-100 text-red-600",
  ACCEPTED: "bg-green-100 text-green-700",
  ARCHIVED: "bg-gray-100 text-gray-400",
};

// Colonnes Kanban : statuts → colonne
export const KANBAN_COLUMNS: {
  id: string;
  label: string;
  statuses: ApplicationStatus[];
  headerColor: string;
}[] = [
  {
    id: "draft",
    label: "Brouillon",
    statuses: ["DRAFT", "READY_TO_SEND"],
    headerColor: "border-gray-300",
  },
  {
    id: "sent",
    label: "Envoyé",
    statuses: ["SENT", "FOLLOW_UP_DUE"],
    headerColor: "border-indigo-400",
  },
  {
    id: "interview",
    label: "Entretien",
    statuses: ["INTERVIEW"],
    headerColor: "border-purple-400",
  },
  {
    id: "closed",
    label: "Clôturé",
    statuses: ["REJECTED", "ACCEPTED", "ARCHIVED"],
    headerColor: "border-gray-400",
  },
];
