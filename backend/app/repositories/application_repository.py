import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.models.application import Application
from app.infrastructure.db.models.application_followup import ApplicationFollowup


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
            .options(joinedload(Application.followups))
            .filter(Application.id == application_id)
            .first()
        )

    def list_all(self) -> list[Application]:
        return (
            self.db.query(Application)
            .options(joinedload(Application.followups))
            .order_by(Application.created_at.desc())
            .all()
        )

    def save(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application

    # ── Follow-ups ────────────────────────────────────────────────────

    def add_followup(self, followup: ApplicationFollowup) -> ApplicationFollowup:
        self.db.add(followup)
        self.db.flush()
        return followup
