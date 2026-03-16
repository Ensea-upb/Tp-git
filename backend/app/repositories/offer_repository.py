import uuid
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.offer import Offer

SortBy = Literal["created_at", "relevance_score"]


class OfferRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Lecture                                                              #
    # ------------------------------------------------------------------ #

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        state: OfferState | None = None,
        is_active: bool | None = True,
        contract_type: str | None = None,
        work_mode: WorkMode | None = None,
        source_id: uuid.UUID | None = None,
        sort_by: SortBy = "created_at",
    ) -> tuple[list[Offer], int]:
        """Retourne (liste d'offres, total) selon les filtres."""
        order_col = Offer.global_score.desc().nulls_last() if sort_by == "relevance_score" else Offer.created_at.desc()
        query = (
            select(Offer)
            .options(joinedload(Offer.company), joinedload(Offer.primary_source))
            .order_by(order_col)
        )
        count_query = select(func.count(Offer.id))

        if state is not None:
            query = query.where(Offer.current_state == state)
            count_query = count_query.where(Offer.current_state == state)

        if is_active is not None:
            query = query.where(Offer.is_active == is_active)
            count_query = count_query.where(Offer.is_active == is_active)

        if contract_type is not None:
            query = query.where(Offer.contract_type == contract_type)
            count_query = count_query.where(Offer.contract_type == contract_type)

        if work_mode is not None:
            query = query.where(Offer.work_mode == work_mode)
            count_query = count_query.where(Offer.work_mode == work_mode)

        if source_id is not None:
            query = query.where(Offer.primary_source_id == source_id)
            count_query = count_query.where(Offer.primary_source_id == source_id)

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

    def get_by_url(self, offer_url: str) -> Offer | None:
        return self.db.execute(
            select(Offer).where(Offer.offer_url == offer_url)
        ).scalar_one_or_none()

    def get_by_checksum(self, checksum: str) -> Offer | None:
        return self.db.execute(
            select(Offer).where(Offer.checksum == checksum)
        ).scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Écriture                                                             #
    # ------------------------------------------------------------------ #

    def create(self, offer: Offer) -> Offer:
        self.db.add(offer)
        self.db.flush()
        return offer

    def update_state(self, offer: Offer, state: OfferState) -> None:
        offer.current_state = state
        self.db.flush()
