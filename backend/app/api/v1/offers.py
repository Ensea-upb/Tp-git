import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.offer import OfferOut, PaginatedOffers
from app.api.schemas.strategy import PrioritizedOfferOut
from app.domain.enums.offer_state import OfferState
from app.domain.enums.user_status import UserStatus
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.session import get_db
from app.repositories.offer_repository import SortBy
from app.services.offer_priority_service import OfferPriorityService
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
    source: str | None = Query(default=None, description="Filtrer par source_type ou nom de source (ex: 'wttj', 'apec')"),
    city: str | None = Query(default=None, description="Filtrer par ville (recherche partielle, ex: 'Paris')"),
    score_min: float | None = Query(default=None, ge=0, le=100, description="Score minimum (ranking ou global)"),
    user_status: UserStatus | None = Query(default=None, description="Filtrer par statut utilisateur"),
    sort_by: SortBy = Query(default="created_at", description="Tri : created_at | relevance_score | personalized_score | ranking_score"),
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
        source=source,
        city=city,
        score_min=score_min,
        user_status=user_status,
        sort_by=sort_by,
    )


@router.get(
    "/prioritized",
    response_model=list[PrioritizedOfferOut],
    summary="Offres priorisées par score composite",
)
def get_prioritized_offers(
    limit: int = Query(default=10, ge=1, le=50, description="Nombre d'offres à retourner"),
    db: Session = Depends(get_db),
) -> list[PrioritizedOfferOut]:
    """
    Retourne les offres actives triées par priority_score décroissant.

    priority_score = 0.6 × ranking_score + 0.4 × matching_score
    """
    items = OfferPriorityService(db).get_prioritized(limit=limit)
    return [
        PrioritizedOfferOut(
            offer_id=item["offer"].id,
            title=item["offer"].normalized_title,
            priority_score=item["priority_score"],
            ranking_score=item["ranking_score"],
            matching_score=item["matching_score"],
            location_text=item["offer"].location_text,
            company_name=item["offer"].company.name if item["offer"].company else None,
        )
        for item in items
    ]


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
