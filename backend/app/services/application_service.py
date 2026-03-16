"""
Application Service — Sprint 7 + Sprint 9.

update_status utilise la machine de transitions domain/state_machine.py.
list_paginated remplace list_all (pagination + filtre par statut).
Sprint 9 : timeline via ApplicationEventRepository, réponse recruteur,
           statistiques candidatures.
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums.application_event_type import ApplicationEventType
from app.domain.enums.application_status import ApplicationStatus
from app.domain.errors import BusinessRuleError, NotFoundError
from app.domain.state_machine import validate_transition
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_event import ApplicationEvent
from app.infrastructure.db.models.application_followup import ApplicationFollowup
from app.infrastructure.db.session import SessionLocal
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.offer_repository import OfferRepository
from app.services.application_assistant_service import ApplicationAssistantService

logger = logging.getLogger(__name__)

# Seuls ces statuts permettent de créer un follow-up
_FOLLOWUP_ALLOWED_STATUSES = {
    ApplicationStatus.SENT,
    ApplicationStatus.FOLLOW_UP_DUE,
    ApplicationStatus.INTERVIEW,
}


class ApplicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ApplicationRepository(db)
        self.event_repo = ApplicationEventRepository(db)

    # ── CRUD ──────────────────────────────────────────────────────────

    def create(
        self,
        offer_id: uuid.UUID,
        source_channel: str | None = None,
        notes: str | None = None,
    ) -> Application:
        if OfferRepository(self.db).get_by_id(offer_id) is None:
            raise NotFoundError(f"Offer {offer_id} not found")

        application = Application(
            offer_id=offer_id,
            status=ApplicationStatus.DRAFT,
            source_channel=source_channel,
            notes=notes,
            drafts_ready=False,
        )
        self.repo.create(application)
        self.event_repo.emit(
            application.id,
            ApplicationEventType.APPLICATION_CREATED,
            {"source_channel": source_channel},
        )
        self.db.commit()
        self.db.refresh(application)
        return application

    def list_paginated(
        self,
        status: ApplicationStatus | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Application], int]:
        return self.repo.list_paginated(status=status, page=page, limit=limit)

    def get(self, application_id: uuid.UUID) -> Application:
        app = self.repo.get(application_id)
        if app is None:
            raise NotFoundError(f"Application {application_id} not found")
        return app

    def update_status(
        self, application_id: uuid.UUID, new_status: ApplicationStatus
    ) -> Application:
        app = self.get(application_id)
        old_status = app.status

        validate_transition(app.status, new_status)

        app.status = new_status
        if new_status == ApplicationStatus.SENT and app.applied_at is None:
            app.applied_at = datetime.utcnow()

        self.event_repo.emit(
            application_id,
            ApplicationEventType.STATUS_CHANGED,
            {"from": old_status.value, "to": new_status.value},
        )
        self.db.commit()
        self.db.refresh(app)
        return app

    def add_followup(
        self,
        application_id: uuid.UUID,
        scheduled_at: datetime,
        notes: str | None = None,
    ) -> ApplicationFollowup:
        app = self.get(application_id)

        if app.status not in _FOLLOWUP_ALLOWED_STATUSES:
            raise BusinessRuleError(
                f"Cannot add a follow-up when status is '{app.status.value}'. "
                f"Allowed: {', '.join(s.value for s in _FOLLOWUP_ALLOWED_STATUSES)}."
            )

        followup = ApplicationFollowup(
            application_id=application_id,
            scheduled_at=scheduled_at,
            notes=notes,
        )
        self.repo.add_followup(followup)

        self.event_repo.emit(
            application_id,
            ApplicationEventType.FOLLOWUP_SCHEDULED,
            {"scheduled_at": scheduled_at.isoformat(), "notes": notes},
        )

        # Transition SENT → FOLLOW_UP_DUE dans le même commit (atomique)
        if app.status == ApplicationStatus.SENT:
            validate_transition(app.status, ApplicationStatus.FOLLOW_UP_DUE)
            app.status = ApplicationStatus.FOLLOW_UP_DUE
            self.event_repo.emit(
                application_id,
                ApplicationEventType.STATUS_CHANGED,
                {"from": ApplicationStatus.SENT.value, "to": ApplicationStatus.FOLLOW_UP_DUE.value},
            )

        self.db.commit()
        self.db.refresh(followup)
        return followup

    # ── Timeline ──────────────────────────────────────────────────────

    def get_timeline(self, application_id: uuid.UUID) -> list[ApplicationEvent]:
        """Retourne la liste chronologique des événements d'une candidature."""
        self.get(application_id)  # lève NotFoundError si absent
        return self.event_repo.get_timeline(application_id)

    # ── Réponse recruteur ─────────────────────────────────────────────

    def add_recruiter_reply(
        self,
        application_id: uuid.UUID,
        message_text: str,
        channel: str | None = None,
    ) -> ApplicationEvent:
        """Enregistre une réponse du recruteur et émet RECRUITER_REPLIED."""
        self.get(application_id)  # lève NotFoundError si absent
        event = self.event_repo.emit(
            application_id,
            ApplicationEventType.RECRUITER_REPLIED,
            {"message_text": message_text, "channel": channel},
        )
        self.db.commit()
        return event

    # ── Statistiques ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """
        Retourne des métriques agrégées sur toutes les candidatures.

        Champs retournés :
          total         — nombre total de candidatures
          interviews    — candidatures en statut INTERVIEW
          rejections    — candidatures en statut REJECTED
          offers        — candidatures en statut ACCEPTED
          response_rate — (interviews + rejections + offers) / total × 100
        """
        rows = self.db.execute(
            select(Application.status, func.count().label("cnt"))
            .group_by(Application.status)
        ).all()

        counts: dict[str, int] = {row.status: row.cnt for row in rows}
        total = sum(counts.values())
        interviews = counts.get(ApplicationStatus.INTERVIEW, 0)
        rejections = counts.get(ApplicationStatus.REJECTED, 0)
        offers = counts.get(ApplicationStatus.ACCEPTED, 0)
        responded = interviews + rejections + offers
        response_rate = round(responded / total * 100, 1) if total > 0 else 0.0

        return {
            "total": total,
            "interviews": interviews,
            "rejections": rejections,
            "offers": offers,
            "response_rate": response_rate,
        }


# ── Tâche de fond : génération LLM ────────────────────────────────────

async def populate_drafts_background(application_id: uuid.UUID) -> None:
    """
    Génère draft_cover_letter et draft_email via LLM et les persiste.
    Positionne drafts_ready=True en fin de tâche (même si LLM offline).
    Crée sa propre session DB (BackgroundTask isolée).
    """
    db: Session = SessionLocal()
    try:
        repo = ApplicationRepository(db)
        event_repo = ApplicationEventRepository(db)
        app = repo.get(application_id)
        if app is None:
            logger.warning("populate_drafts_background: application %s not found", application_id)
            return

        assistant = ApplicationAssistantService(db)

        try:
            cover = await assistant.generate_cover_letter(app.offer_id)
            subject_cl = cover.get("subject", "")
            body_cl = cover.get("body", "")
            app.draft_cover_letter = f"{subject_cl}\n\n{body_cl}".strip() if body_cl else None
        except Exception:
            logger.exception("LLM cover letter failed for application %s", application_id)

        try:
            email = await assistant.generate_application_email(app.offer_id)
            subject_em = email.get("subject", "")
            body_em = email.get("body", "")
            app.draft_email = f"{subject_em}\n\n{body_em}".strip() if body_em else None
        except Exception:
            logger.exception("LLM email draft failed for application %s", application_id)

        app.drafts_ready = True
        event_repo.emit(
            application_id,
            ApplicationEventType.DRAFTS_READY,
            {"cover_letter_ready": app.draft_cover_letter is not None,
             "email_ready": app.draft_email is not None},
        )
        db.commit()
    finally:
        db.close()
