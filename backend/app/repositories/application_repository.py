import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.domain.enums.application_status import ApplicationStatus
from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_followup import ApplicationFollowup
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.source import Source


def _base_options():
    """Options de chargement communes : followups + offer + source de l'offre."""
    return [
        joinedload(Application.followups),
        joinedload(Application.offer).joinedload(Offer.primary_source),
    ]


class ApplicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application

    def get(self, application_id: uuid.UUID) -> Application | None:
        return (
            self.db.query(Application)
            .options(*_base_options())
            .filter(Application.id == application_id)
            .first()
        )

    def list_paginated(
        self,
        status: ApplicationStatus | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Application], int]:
        query = self.db.query(Application).options(*_base_options())
        if status is not None:
            query = query.filter(Application.status == status)
        total: int = query.count()
        offset = (page - 1) * limit
        items = query.order_by(Application.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def save(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application

    # ── Follow-ups ────────────────────────────────────────────────────

    def add_followup(self, followup: ApplicationFollowup) -> ApplicationFollowup:
        self.db.add(followup)
        self.db.flush()
        return followup
