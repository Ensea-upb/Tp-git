import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.offer import OfferOut, PaginatedOffers
from app.domain.enums.offer_state import OfferState
from app.domain.enums.user_status import UserStatus
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.session import get_db
from app.repositories.offer_repository import SortBy
from app.services.offer_service import OfferService

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("", response_model=PaginatedOffers, summary="Liste paginée des offres")
def list_offers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    state: OfferState | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    contract_type: str | None = Query(default=None),
    work_mode: WorkMode | None = Query(default=None),
    source_id: uuid.UUID | None = Query(default=None),
    user_status: UserStatus | None = Query(default=None, description="Filtrer par statut utilisateur"),
    sort_by: SortBy = Query(default="created_at"),
    db: Session = Depends(get_db),
) -> PaginatedOffers:
    service = OfferService(db)
    return service.list_offers(
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


@router.get("/{offer_id}", response_model=OfferOut, summary="Détail d'une offre")
def get_offer(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> OfferOut:
    service = OfferService(db)
    offer = service.get_offer(offer_id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    return offer
