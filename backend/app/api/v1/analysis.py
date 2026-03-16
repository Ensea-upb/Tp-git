"""
LLM analysis endpoints.
POST /v1/offers/{id}/analyze       — trigger analysis (BackgroundTask)
GET  /v1/offers/{id}/analysis      — get stored analysis
POST /v1/offers/{id}/match-profile — trigger profile match (BackgroundTask)
GET  /v1/offers/{id}/match         — get stored match
"""
import uuid
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.analysis import OfferLLMAnalysisOut, ProfileMatchOut
from app.repositories.offer_llm_analysis_repository import OfferLLMAnalysisRepository
from app.repositories.profile_match_llm_repository import ProfileMatchLLMRepository
from app.repositories.offer_repository import OfferRepository
from app.services.offer_llm_analysis_service import OfferLLMAnalysisService
from app.services.profile_matching_service import ProfileMatchingService

router = APIRouter(prefix="/offers", tags=["llm-analysis"])
logger = logging.getLogger(__name__)


def _run_async_in_background(coro):
    """Run async coroutine inside a BackgroundTask (sync context)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)


@router.post("/{offer_id}/analyze", status_code=202)
def trigger_analysis(
    offer_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    offer = OfferRepository(db).get_by_id(offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")

    background_tasks.add_task(
        _run_async_in_background,
        OfferLLMAnalysisService(None).analyze_offer_background(offer_id),
    )
    return {"status": "queued", "offer_id": str(offer_id)}


@router.get("/{offer_id}/analysis", response_model=OfferLLMAnalysisOut)
def get_analysis(offer_id: uuid.UUID, db: Session = Depends(get_db)):
    analysis = OfferLLMAnalysisRepository(db).get(offer_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="No analysis found for this offer")
    return analysis


@router.post("/{offer_id}/match-profile", status_code=202)
def trigger_profile_match(
    offer_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    offer = OfferRepository(db).get_by_id(offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")

    background_tasks.add_task(
        _run_async_in_background,
        ProfileMatchingService(None).match_offer_background(offer_id),
    )
    return {"status": "queued", "offer_id": str(offer_id)}


@router.get("/{offer_id}/match", response_model=ProfileMatchOut)
def get_profile_match(offer_id: uuid.UUID, db: Session = Depends(get_db)):
    match = ProfileMatchLLMRepository(db).get(offer_id)
    if match is None:
        raise HTTPException(status_code=404, detail="No profile match found for this offer")
    return match
