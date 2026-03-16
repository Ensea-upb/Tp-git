"""
Application Service — Sprint 6.
Gère le cycle de vie des candidatures.
Les brouillons LLM sont générés en tâche de fond après création.
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.enums.application_status import ApplicationStatus
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_followup import ApplicationFollowup
from app.infrastructure.db.session import SessionLocal
from app.repositories.application_repository import ApplicationRepository
from app.repositories.offer_repository import OfferRepository
from app.services.application_assistant_service import ApplicationAssistantService

logger = logging.getLogger(__name__)


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
            raise ValueError(f"Offer {offer_id} not found")

        application = Application(
            offer_id=offer_id,
            status=ApplicationStatus.DRAFT,
            source_channel=source_channel,
            notes=notes,
        )
        self.repo.create(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def list_all(self) -> list[Application]:
        return self.repo.list_all()

    def get(self, application_id: uuid.UUID) -> Application:
        app = self.repo.get(application_id)
        if app is None:
            raise ValueError(f"Application {application_id} not found")
        return app

    def update_status(
        self, application_id: uuid.UUID, new_status: ApplicationStatus
    ) -> Application:
        app = self.get(application_id)
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
        # Vérifie que la candidature existe
        self.get(application_id)

        followup = ApplicationFollowup(
            application_id=application_id,
            scheduled_at=scheduled_at,
            notes=notes,
        )
        self.repo.add_followup(followup)
        self.db.commit()
        self.db.refresh(followup)

        # Passer le statut à FOLLOW_UP_DUE si encore en SENT
        app = self.repo.get(application_id)
        if app and app.status == ApplicationStatus.SENT:
            app.status = ApplicationStatus.FOLLOW_UP_DUE
            self.db.commit()

        return followup


# ── Tâche de fond : génération LLM ────────────────────────────────────

async def populate_drafts_background(application_id: uuid.UUID) -> None:
    """
    Génère draft_cover_letter et draft_email via LLM et les persiste.
    Appelée en BackgroundTask — crée sa propre session DB.
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

        db.commit()
    finally:
        db.close()
