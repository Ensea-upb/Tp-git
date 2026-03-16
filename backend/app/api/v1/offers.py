import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.offer import OfferOut, PaginatedOffers
from app.domain.enums.offer_state import OfferState
from app.infrastructure.db.session import get_db
from app.services.offer_service import OfferService

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("", response_model=PaginatedOffers, summary="Liste paginée des offres")
def list_offers(
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    page_size: int = Query(default=20, ge=1, le=100, description="Offres par page"),
    state: OfferState | None = Query(default=None, description="Filtrer par état"),
    is_active: bool | None = Query(default=True, description="Filtrer par statut actif"),
    db: Session = Depends(get_db),
) -> PaginatedOffers:
    """Retourne la liste paginée des offres avec filtres optionnels."""
    service = OfferService(db)
    return service.list_offers(page=page, page_size=page_size, state=state, is_active=is_active)


@router.get("/{offer_id}", response_model=OfferOut, summary="Détail d'une offre")
def get_offer(
    offer_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> OfferOut:
    """Retourne le détail complet d'une offre par son UUID."""
    service = OfferService(db)
    offer = service.get_offer(offer_id)
    if offer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found",
        )
    return offer
