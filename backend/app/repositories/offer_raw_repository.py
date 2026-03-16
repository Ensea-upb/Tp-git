import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models.offer_raw import OfferRaw


class OfferRawRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, offer_raw_id: uuid.UUID) -> OfferRaw | None:
        return self.db.execute(
            select(OfferRaw).where(OfferRaw.id == offer_raw_id)
        ).scalar_one_or_none()

    def get_by_url(self, url: str) -> OfferRaw | None:
        return self.db.execute(
            select(OfferRaw).where(OfferRaw.offer_url == url)
        ).scalar_one_or_none()

    def get_by_source_and_external_id(
        self, source_id: uuid.UUID, external_offer_id: str
    ) -> OfferRaw | None:
        return self.db.execute(
            select(OfferRaw).where(
                OfferRaw.source_id == source_id,
                OfferRaw.external_offer_id == external_offer_id,
            )
        ).scalar_one_or_none()

    def create(self, offer_raw: OfferRaw) -> OfferRaw:
        self.db.add(offer_raw)
        self.db.flush()
        return offer_raw

    def update_parsing_status(self, offer_raw: OfferRaw, status: str) -> None:
        offer_raw.parsing_status = status
        self.db.flush()
