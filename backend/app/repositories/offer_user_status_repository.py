import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums.user_status import UserStatus
from app.infrastructure.db.models.offer_user_status import OfferUserStatus


class OfferUserStatusRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, offer_id: uuid.UUID) -> OfferUserStatus | None:
        return self.db.execute(
            select(OfferUserStatus).where(OfferUserStatus.offer_id == offer_id)
        ).scalar_one_or_none()

    def set_status(self, offer_id: uuid.UUID, status: UserStatus) -> OfferUserStatus:
        """Crée ou met à jour le statut d'une offre."""
        existing = self.get(offer_id)
        if existing:
            existing.status = status
            self.db.flush()
            return existing
        row = OfferUserStatus(offer_id=offer_id, status=status)
        self.db.add(row)
        self.db.flush()
        return row

    def remove(self, offer_id: uuid.UUID) -> bool:
        """Supprime le statut. Retourne True si un statut existait."""
        existing = self.get(offer_id)
        if existing:
            self.db.delete(existing)
            self.db.flush()
            return True
        return False
