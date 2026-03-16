import uuid

from sqlalchemy.orm import Session

from app.api.schemas.offer import OfferListItem, OfferOut, PaginatedOffers
from app.domain.enums.offer_state import OfferState
from app.domain.enums.user_status import UserStatus
from app.domain.enums.work_mode import WorkMode
from app.repositories.offer_repository import OfferRepository, SortBy


class OfferService:
    def __init__(self, db: Session) -> None:
        self.repo = OfferRepository(db)

    def list_offers(
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
    ) -> PaginatedOffers:
        offers, total = self.repo.get_all(
            page=page,
            page_size=page_size,
            state=state,
            is_active=is_active,
            contract_type=contract_type,
            work_mode=work_mode,
            source_id=source_id,
            user_status=user_status,
            sort_by=sort_by,
        )
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
