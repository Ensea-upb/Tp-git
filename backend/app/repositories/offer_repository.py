import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums.offer_state import OfferState
from app.infrastructure.db.models.offer import Offer


class OfferRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        state: OfferState | None = None,
        is_active: bool | None = True,
    ) -> tuple[list[Offer], int]:
        """Retourne (liste d'offres, total) selon les filtres."""
        query = (
            select(Offer)
            .options(joinedload(Offer.company), joinedload(Offer.primary_source))
            .order_by(Offer.created_at.desc())
        )
        count_query = select(func.count(Offer.id))

        if state is not None:
            query = query.where(Offer.current_state == state)
            count_query = count_query.where(Offer.current_state == state)

        if is_active is not None:
            query = query.where(Offer.is_active == is_active)
            count_query = count_query.where(Offer.is_active == is_active)

        total = self.db.execute(count_query).scalar_one()
        offset = (page - 1) * page_size
        offers = list(self.db.execute(query.offset(offset).limit(page_size)).scalars().unique())

        return offers, total

    def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        """Retourne une offre par son UUID, avec ses relations."""
        result = self.db.execute(
            select(Offer)
            .options(joinedload(Offer.company), joinedload(Offer.primary_source))
            .where(Offer.id == offer_id)
        )
        return result.scalar_one_or_none()
