"""Repository pour les événements de la timeline des candidatures."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums.application_event_type import ApplicationEventType
from app.infrastructure.db.models.application_event import ApplicationEvent


class ApplicationEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_timeline(self, application_id: uuid.UUID) -> list[ApplicationEvent]:
        """Retourne tous les événements d'une candidature, ordre chronologique."""
        return list(
            self.db.execute(
                select(ApplicationEvent)
                .where(ApplicationEvent.application_id == application_id)
                .order_by(ApplicationEvent.created_at)
            ).scalars().all()
        )

    def emit(
        self,
        application_id: uuid.UUID,
        event_type: ApplicationEventType,
        payload: dict | None = None,
    ) -> ApplicationEvent:
        """Crée et persiste un événement (flush sans commit — l'appelant committe)."""
        event = ApplicationEvent(
            application_id=application_id,
            event_type=event_type,
            payload_json=payload or {},
        )
        self.db.add(event)
        self.db.flush()
        return event
