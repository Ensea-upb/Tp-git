"""
Endpoints d'action utilisateur sur les offres.

POST   /v1/offers/{id}/favorite    → FAVORITE
DELETE /v1/offers/{id}/favorite    → supprime le statut
POST   /v1/offers/{id}/shortlist   → SHORTLISTED
DELETE /v1/offers/{id}/shortlist   → supprime le statut
POST   /v1/offers/{id}/apply       → APPLIED
DELETE /v1/offers/{id}/apply       → supprime le statut
POST   /v1/offers/{id}/reject      → REJECTED
DELETE /v1/offers/{id}/reject      → supprime le statut

Note : les statuts sont exclusifs — un seul par offre.
POST vers un autre statut remplace le précédent.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.offer_status import OfferUserStatusOut
from app.domain.enums.user_status import UserStatus
from app.infrastructure.db.session import get_db
from app.repositories.offer_repository import OfferRepository
from app.repositories.offer_user_status_repository import OfferUserStatusRepository

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _require_offer(offer_id: uuid.UUID, db: Session) -> None:
    repo = OfferRepository(db)
    if repo.get_by_id(offer_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offre {offer_id} introuvable.",
        )


def _set(offer_id: uuid.UUID, new_status: UserStatus, db: Session) -> OfferUserStatusOut:
    _require_offer(offer_id, db)
    repo = OfferUserStatusRepository(db)
    row = repo.set_status(offer_id, new_status)
    db.commit()
    db.refresh(row)
    return OfferUserStatusOut.model_validate(row)


def _remove(offer_id: uuid.UUID, db: Session) -> None:
    _require_offer(offer_id, db)
    repo = OfferUserStatusRepository(db)
    repo.remove(offer_id)
    db.commit()


# ── Favorite ──────────────────────────────────────────────────────────

@router.post(
    "/{offer_id}/favorite",
    response_model=OfferUserStatusOut,
    status_code=status.HTTP_200_OK,
    summary="Marquer une offre comme favorite",
)
def add_favorite(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> OfferUserStatusOut:
    return _set(offer_id, UserStatus.FAVORITE, db)


@router.delete(
    "/{offer_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer le marquage favori",
)
def remove_favorite(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _remove(offer_id, db)


# ── Shortlist ─────────────────────────────────────────────────────────

@router.post(
    "/{offer_id}/shortlist",
    response_model=OfferUserStatusOut,
    status_code=status.HTTP_200_OK,
    summary="Ajouter une offre à la shortlist",
)
def add_shortlist(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> OfferUserStatusOut:
    return _set(offer_id, UserStatus.SHORTLISTED, db)


@router.delete(
    "/{offer_id}/shortlist",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirer de la shortlist",
)
def remove_shortlist(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _remove(offer_id, db)


# ── Apply ─────────────────────────────────────────────────────────────

@router.post(
    "/{offer_id}/apply",
    response_model=OfferUserStatusOut,
    status_code=status.HTTP_200_OK,
    summary="Marquer une offre comme postulée",
)
def apply_offer(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> OfferUserStatusOut:
    return _set(offer_id, UserStatus.APPLIED, db)


@router.delete(
    "/{offer_id}/apply",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Annuler la candidature sur une offre",
)
def remove_apply(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _remove(offer_id, db)


# ── Reject ────────────────────────────────────────────────────────────

@router.post(
    "/{offer_id}/reject",
    response_model=OfferUserStatusOut,
    status_code=status.HTTP_200_OK,
    summary="Rejeter une offre",
)
def reject_offer(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> OfferUserStatusOut:
    return _set(offer_id, UserStatus.REJECTED, db)


@router.delete(
    "/{offer_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Annuler le rejet d'une offre",
)
def remove_reject(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    _remove(offer_id, db)
