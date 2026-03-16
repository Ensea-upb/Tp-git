import uuid

from sqlalchemy.orm import Session

from app.api.schemas.offer import OfferListItem, OfferOut, PaginatedOffers
from app.domain.enums.offer_state import OfferState
from app.repositories.offer_repository import OfferRepository


class OfferService:
    def __init__(self, db: Session) -> None:
        self.repo = OfferRepository(db)

    def list_offers(
        self,
        page: int = 1,
        page_size: int = 20,
        state: OfferState | None = None,
        is_active: bool | None = True,
    ) -> PaginatedOffers:
        offers, total = self.repo.get_all(page=page, page_size=page_size, state=state, is_active=is_active)
        items = [OfferListItem.model_validate(o) for o in offers]
        return PaginatedOffers(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    def get_offer(self, offer_id: uuid.UUID) -> OfferOut | None:
        offer = self.repo.get_by_id(offer_id)
        if offer is None:
            return None
        return OfferOut.model_validate(offer)
