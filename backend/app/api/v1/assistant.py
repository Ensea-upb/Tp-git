"""
Application assistant endpoints.
All are async (LLM calls).
POST /v1/offers/{id}/cover-letter     — generate cover letter
POST /v1/offers/{id}/email            — generate application email
POST /v1/offers/{id}/interview-prep   — generate interview prep
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.infrastructure.db.session import get_db
from app.repositories.offer_repository import OfferRepository
from app.services.application_assistant_service import ApplicationAssistantService

router = APIRouter(prefix="/offers", tags=["assistant"], dependencies=[Depends(verify_api_key)])
logger = logging.getLogger(__name__)


@router.post("/{offer_id}/cover-letter")
async def generate_cover_letter(offer_id: uuid.UUID, db: Session = Depends(get_db)):
    _check_offer_exists(offer_id, db)
    service = ApplicationAssistantService(db)
    try:
        result = await service.generate_cover_letter(offer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Cover letter generation failed: %s", e)
        raise HTTPException(status_code=503, detail="LLM unavailable. Is Ollama running?")
    return result


@router.post("/{offer_id}/email")
async def generate_application_email(offer_id: uuid.UUID, db: Session = Depends(get_db)):
    _check_offer_exists(offer_id, db)
    service = ApplicationAssistantService(db)
    try:
        result = await service.generate_application_email(offer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Email generation failed: %s", e)
        raise HTTPException(status_code=503, detail="LLM unavailable. Is Ollama running?")
    return result


@router.post("/{offer_id}/interview-prep")
async def generate_interview_prep(offer_id: uuid.UUID, db: Session = Depends(get_db)):
    _check_offer_exists(offer_id, db)
    service = ApplicationAssistantService(db)
    try:
        result = await service.generate_interview_prep(offer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Interview prep generation failed: %s", e)
        raise HTTPException(status_code=503, detail="LLM unavailable. Is Ollama running?")
    return result


def _check_offer_exists(offer_id: uuid.UUID, db: Session) -> None:
    offer = OfferRepository(db).get_by_id(offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
