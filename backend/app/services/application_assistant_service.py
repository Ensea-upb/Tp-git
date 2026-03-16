"""
Application Assistant Service.
Generates cover letters, emails, and interview prep using LLM.
Results are returned directly (not persisted to DB).
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.candidate_profile_repository import CandidateProfileRepository
from app.repositories.offer_repository import OfferRepository
from app.services.llm.llm_service import call_llm_json
from app.services.llm.prompt_builder import (
    build_cover_letter_prompt,
    build_application_email_prompt,
    build_interview_prep_prompt,
)

logger = logging.getLogger(__name__)


class ApplicationAssistantService:
    def __init__(self, db: Session):
        self.db = db
        self.offer_repo = OfferRepository(db)
        self.profile_repo = CandidateProfileRepository(db)

    async def generate_cover_letter(self, offer_id: uuid.UUID) -> dict:
        offer, profile = self._get_offer_and_profile(offer_id)
        prompt = build_cover_letter_prompt(offer, profile)
        result = await call_llm_json(
            prompt=prompt,
            model=settings.llm_model_hq,
            max_tokens=800,
            temperature=0.3,
            db_session=self.db,
        )
        self.db.commit()  # persist cache
        return result or {"error": "LLM did not return valid JSON"}

    async def generate_application_email(self, offer_id: uuid.UUID) -> dict:
        offer, profile = self._get_offer_and_profile(offer_id)
        prompt = build_application_email_prompt(offer, profile)
        result = await call_llm_json(
            prompt=prompt,
            model=settings.llm_model_default,
            max_tokens=400,
            temperature=0.2,
            db_session=self.db,
        )
        self.db.commit()
        return result or {"error": "LLM did not return valid JSON"}

    async def generate_interview_prep(self, offer_id: uuid.UUID) -> dict:
        offer, profile = self._get_offer_and_profile(offer_id)
        prompt = build_interview_prep_prompt(offer, profile)
        result = await call_llm_json(
            prompt=prompt,
            model=settings.llm_model_hq,
            max_tokens=700,
            temperature=0.2,
            db_session=self.db,
        )
        self.db.commit()
        return result or {"error": "LLM did not return valid JSON"}

    def _get_offer_and_profile(self, offer_id: uuid.UUID):
        offer = self.offer_repo.get_by_id(offer_id)
        if offer is None:
            raise ValueError(f"Offer {offer_id} not found")
        profile = self.profile_repo.get_default()
        if profile is None:
            raise ValueError("No candidate profile found. Create one at /v1/candidate first.")
        return offer, profile
