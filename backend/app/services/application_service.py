"""
Application Service — Sprint 7.
update_status utilise la machine de transitions domain/state_machine.py.
list_paginated remplace list_all (pagination + filtre par statut).
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.enums.application_status import ApplicationStatus
from app.domain.errors import BusinessRuleError, NotFoundError
from app.domain.state_machine import validate_transition
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_followup import ApplicationFollowup
from app.infrastructure.db.session import SessionLocal
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

        # Machine de transitions — lève BusinessRuleError si interdit
        validate_transition(app.status, new_status)

        app.status = new_status
        if new_status == ApplicationStatus.SENT and app.applied_at is None:
            app.applied_at = datetime.utcnow()
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

        # Transition SENT → FOLLOW_UP_DUE dans le même commit (atomique)
        if app.status == ApplicationStatus.SENT:
            validate_transition(app.status, ApplicationStatus.FOLLOW_UP_DUE)
            app.status = ApplicationStatus.FOLLOW_UP_DUE

        self.db.commit()
        self.db.refresh(followup)
        return followup


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
        db.commit()
    finally:
        db.close()
