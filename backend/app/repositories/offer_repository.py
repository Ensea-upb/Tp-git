import uuid
from typing import Literal

from sqlalchemy import func, outerjoin, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.domain.enums.offer_state import OfferState
from app.domain.enums.user_status import UserStatus
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.models.offer import Offer
from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis
from app.infrastructure.db.models.offer_user_status import OfferUserStatus
from app.infrastructure.db.models.profile_match_llm import ProfileMatchLLM

SortBy = Literal["created_at", "relevance_score", "personalized_score"]


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
        user_status: UserStatus | None = None,
        sort_by: SortBy = "created_at",
    ) -> tuple[list[Offer], int]:
        """Retourne (liste d'offres, total) selon les filtres."""
        if sort_by == "personalized_score":
            order_col = Offer.personalized_score.desc().nulls_last()
        elif sort_by == "relevance_score":
            order_col = Offer.global_score.desc().nulls_last()
        else:
            order_col = Offer.created_at.desc()

        # Base query avec LEFT JOIN sur offer_user_statuses
        j = outerjoin(Offer, OfferUserStatus, Offer.id == OfferUserStatus.offer_id)
        query = (
            select(Offer)
            .select_from(j)
            .options(
                joinedload(Offer.company),
                joinedload(Offer.primary_source),
                contains_eager(Offer.user_status),
            )
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

        if user_status is not None:
            query = query.where(OfferUserStatus.status == user_status)
            count_query = count_query.join(
                OfferUserStatus, Offer.id == OfferUserStatus.offer_id
            ).where(OfferUserStatus.status == user_status)

        total = self.db.execute(count_query).scalar_one()
        offset = (page - 1) * page_size
        offers = list(self.db.execute(query.offset(offset).limit(page_size)).scalars().unique())

        return offers, total

    def get_by_id(self, offer_id: uuid.UUID) -> Offer | None:
        result = self.db.execute(
            select(Offer)
            .options(
                joinedload(Offer.company),
                joinedload(Offer.primary_source),
                joinedload(Offer.user_status),
                joinedload(Offer.llm_analysis),
                joinedload(Offer.profile_match),
            )
            .where(Offer.id == offer_id)
        )
        return result.scalar_one_or_none()

    def get_all_for_rescore(
        self,
        active_only: bool = False,
        offer_id: uuid.UUID | None = None,
    ) -> list[Offer]:
        """Retourne les offres à rescorer (sans pagination)."""
        query = select(Offer)
        if active_only:
            query = query.where(Offer.is_active == True)  # noqa: E712
        if offer_id is not None:
            query = query.where(Offer.id == offer_id)
        return list(self.db.execute(query).scalars().all())

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
