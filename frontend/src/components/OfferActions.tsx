"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { setOfferAction, removeOfferAction } from "@/lib/api";
import type { UserStatusValue } from "@/types/offer";
import { USER_STATUS_LABELS } from "@/lib/constants";

interface OfferActionsProps {
  offerId: string;
  currentStatus: UserStatusValue | null;
  /** Compact : affiche des petits boutons icône (pour les cartes) */
  compact?: boolean;
}

const ACTIONS: { action: "favorite" | "shortlist" | "reject"; status: UserStatusValue; emoji: string }[] = [
  { action: "favorite", status: "FAVORITE", emoji: "★" },
  { action: "shortlist", status: "SHORTLISTED", emoji: "✓" },
  { action: "reject", status: "REJECTED", emoji: "✕" },
];

export default function OfferActions({ offerId, currentStatus, compact = false }: OfferActionsProps) {
  const [status, setStatus] = useState<UserStatusValue | null>(currentStatus);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const handleAction = (action: "favorite" | "shortlist" | "reject", targetStatus: UserStatusValue) => {
    startTransition(async () => {
      try {
        if (status === targetStatus) {
          // Toggle off
          await removeOfferAction(offerId, action);
          setStatus(null);
        } else {
          await setOfferAction(offerId, action);
          setStatus(targetStatus);
        }
        router.refresh();
      } catch {
        // Silently fail — UI stays consistent
      }
    });
  };

  if (compact) {
    return (
      <div className="flex items-center gap-1" onClick={(e) => e.preventDefault()}>
        {ACTIONS.map(({ action, status: s, emoji }) => (
          <button
            key={action}
            disabled={isPending}
            onClick={() => handleAction(action, s)}
            title={USER_STATUS_LABELS[s]}
            className={`w-7 h-7 rounded-full text-sm font-bold transition-colors border ${
              status === s
                ? s === "FAVORITE"
                  ? "bg-amber-100 text-amber-600 border-amber-300"
                  : s === "SHORTLISTED"
                  ? "bg-green-100 text-green-600 border-green-300"
                  : "bg-red-100 text-red-500 border-red-300"
                : "bg-white text-gray-400 border-gray-200 hover:border-gray-400 hover:text-gray-600"
            } disabled:opacity-50`}
          >
            {emoji}
          </button>
        ))}
      </div>
    );
  }

  // Full version for detail page
  return (
    <div className="space-y-2">
      {ACTIONS.map(({ action, status: s, emoji }) => {
        const isActive = status === s;
        let btnClass = "w-full px-4 py-2 text-sm rounded-lg font-medium transition-colors border ";
        if (isActive) {
          if (s === "FAVORITE") btnClass += "bg-amber-50 text-amber-700 border-amber-300";
          else if (s === "SHORTLISTED") btnClass += "bg-green-50 text-green-700 border-green-300";
          else btnClass += "bg-red-50 text-red-600 border-red-300";
        } else {
          btnClass += "bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300";
        }

        return (
          <button
            key={action}
            disabled={isPending}
            onClick={() => handleAction(action, s)}
            className={`${btnClass} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <span className="mr-2">{emoji}</span>
            {isActive ? `Retirer "${USER_STATUS_LABELS[s]}"` : USER_STATUS_LABELS[s]}
          </button>
        );
      })}
    </div>
  );
}
