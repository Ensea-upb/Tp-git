"""
ApplicationStrategyService — Sprint 10.

Génère des recommandations d'action sur les candidatures :
  APPLY_NOW         — offres haute priorité (ranking_score ≥ 70) sans candidature en cours
  SEND_FOLLOWUP     — candidatures en FOLLOW_UP_DUE
  PREPARE_INTERVIEW — candidatures en INTERVIEW
  ARCHIVE_STALE     — candidatures SENT dont le dernier événement date de > 21 jours

Chaque action porte : action_type, reason, priority (1=faible, 2=moyen, 3=élevé),
et optionnellement application_id ou offer_id selon la source.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.application_status import ApplicationStatus
from app.domain.enums.strategy_action_type import StrategyActionType
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_event import ApplicationEvent
from app.infrastructure.db.models.offer import Offer

_STALE_DAYS = 21
_APPLY_NOW_MIN_SCORE = 70.0
_APPLY_NOW_LIMIT = 5

# Statuts indiquant une candidature encore en vie — utilisé pour exclure les
# offres déjà en cours de traitement de la suggestion APPLY_NOW.
# Les statuts terminaux (REJECTED, ACCEPTED, ARCHIVED) ne bloquent pas la
# suggestion : l'offre peut être repostée et mérite d'être re-signalée.
_ACTIVE_APPLICATION_STATUSES = frozenset({
    ApplicationStatus.DRAFT,
    ApplicationStatus.READY_TO_SEND,
    ApplicationStatus.SENT,
    ApplicationStatus.FOLLOW_UP_DUE,
    ApplicationStatus.INTERVIEW,
})


@dataclass
class StrategyAction:
    action_type: StrategyActionType
    reason: str
    priority: int
    application_id: uuid.UUID | None = field(default=None)
    offer_id: uuid.UUID | None = field(default=None)


class ApplicationStrategyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def recommend_actions(self) -> list[StrategyAction]:
        """
        Retourne la liste des actions recommandées, triées par priorité décroissante.

        Ordre de priorité :
          3 (élevé)  — PREPARE_INTERVIEW, APPLY_NOW
          2 (moyen)  — SEND_FOLLOWUP
          1 (faible) — ARCHIVE_STALE
        """
        actions: list[StrategyAction] = []
        actions.extend(self._interview_actions())
        actions.extend(self._apply_now_actions())
        actions.extend(self._followup_actions())
        actions.extend(self._stale_actions())
        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    # ── Sources d'actions ─────────────────────────────────────────────

    def _interview_actions(self) -> list[StrategyAction]:
        """Candidatures en phase d'entretien → PREPARE_INTERVIEW (priorité 3)."""
        apps = self.db.execute(
            select(Application).where(Application.status == ApplicationStatus.INTERVIEW)
        ).scalars().all()
        return [
            StrategyAction(
                action_type=StrategyActionType.PREPARE_INTERVIEW,
                application_id=app.id,
                reason="Candidature en phase d'entretien — préparez vos réponses.",
                priority=3,
            )
            for app in apps
        ]

    def _followup_actions(self) -> list[StrategyAction]:
        """Candidatures en FOLLOW_UP_DUE → SEND_FOLLOWUP (priorité 2)."""
        apps = self.db.execute(
            select(Application).where(Application.status == ApplicationStatus.FOLLOW_UP_DUE)
        ).scalars().all()
        return [
            StrategyAction(
                action_type=StrategyActionType.SEND_FOLLOWUP,
                application_id=app.id,
                reason="Relance planifiée en attente d'envoi.",
                priority=2,
            )
            for app in apps
        ]

    def _stale_actions(self) -> list[StrategyAction]:
        """
        Détection des candidatures stale.

        Règle : status = SENT ET dernier événement enregistré > 21 jours
        (ou aucun événement). → ARCHIVE_STALE (priorité 1).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_DAYS)

        last_event_subq = (
            select(
                ApplicationEvent.application_id,
                func.max(ApplicationEvent.created_at).label("last_event_at"),
            )
            .group_by(ApplicationEvent.application_id)
            .subquery()
        )

        stale_apps = self.db.execute(
            select(Application)
            .outerjoin(last_event_subq, Application.id == last_event_subq.c.application_id)
            .where(Application.status == ApplicationStatus.SENT)
            .where(
                or_(
                    last_event_subq.c.last_event_at < cutoff,
                    last_event_subq.c.last_event_at.is_(None),
                )
            )
        ).scalars().all()

        return [
            StrategyAction(
                action_type=StrategyActionType.ARCHIVE_STALE,
                application_id=app.id,
                reason=(
                    f"Sans nouvelles depuis plus de {_STALE_DAYS} jours "
                    "— envisagez d'archiver cette candidature."
                ),
                priority=1,
            )
            for app in stale_apps
        ]

    def _apply_now_actions(self) -> list[StrategyAction]:
        """
        Offres actives hautement notées sans candidature en cours → APPLY_NOW (priorité 3).

        Critères : ranking_score ≥ 70, is_active=True, aucune Application existante.
        """
        applied_offer_ids = (
            select(Application.offer_id)
            .where(Application.status.in_(_ACTIVE_APPLICATION_STATUSES))
            .distinct()
        )
        top_offers = self.db.execute(
            select(Offer)
            .where(Offer.is_active == True)  # noqa: E712
            .where(Offer.ranking_score >= _APPLY_NOW_MIN_SCORE)
            .where(~Offer.id.in_(applied_offer_ids))
            .order_by(Offer.ranking_score.desc())
            .limit(_APPLY_NOW_LIMIT)
        ).scalars().all()

        return [
            StrategyAction(
                action_type=StrategyActionType.APPLY_NOW,
                offer_id=offer.id,
                reason=(
                    f"Offre très bien notée (score {float(offer.ranking_score):.0f}/100) "
                    "— postulez sans attendre."
                ),
                priority=3,
            )
            for offer in top_offers
        ]
