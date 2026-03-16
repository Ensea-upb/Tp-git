"""
Profile Matching Service.
LLM-based offer × candidate profile compatibility assessment.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.db.models.profile_match_llm import ProfileMatchLLM
from app.repositories.candidate_profile_repository import CandidateProfileRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.profile_match_llm_repository import ProfileMatchLLMRepository
from app.services.llm.llm_service import call_llm_json
from app.services.llm.prompt_builder import build_profile_match_prompt

logger = logging.getLogger(__name__)


class ProfileMatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.offer_repo = OfferRepository(db)
        self.profile_repo = CandidateProfileRepository(db)
        self.match_repo = ProfileMatchLLMRepository(db)

    async def match_offer(self, offer_id: uuid.UUID) -> ProfileMatchLLM:
        offer = self.offer_repo.get_by_id(offer_id)
        if offer is None:
            raise ValueError(f"Offer {offer_id} not found")

        profile = self.profile_repo.get_default()
        if profile is None:
            raise ValueError("No candidate profile found. Create one at /v1/candidate first.")

        model = settings.llm_model_hq  # use higher quality model for matching
        prompt = build_profile_match_prompt(offer, profile)

        match = ProfileMatchLLM(
            offer_id=offer_id,
            model_used=model,
            match_status="RUNNING",
        )

        try:
            parsed = await call_llm_json(
                prompt=prompt,
                model=model,
                max_tokens=600,
                temperature=0.0,
                db_session=self.db,
            )
            if parsed and isinstance(parsed, dict):
                raw_score = parsed.get("match_score")
                if raw_score is not None:
                    try:
                        match.match_score = max(0, min(100, float(raw_score)))
                    except (TypeError, ValueError):
                        pass
                match.strengths = parsed.get("strengths")
                match.gaps = parsed.get("gaps")
                match.recommendation = parsed.get("recommendation")
                match.match_status = "DONE"
            else:
                match.match_status = "FAILED"
                match.raw_response = str(parsed)
        except Exception as e:
            logger.error("Profile matching failed for offer %s: %s", offer_id, e)
            match.match_status = "FAILED"
            match.raw_response = str(e)

        result = self.match_repo.upsert(match)
        self.db.commit()
        return result

    async def match_offer_background(self, offer_id: uuid.UUID) -> None:
        from app.infrastructure.db.session import SessionLocal
        db = SessionLocal()
        try:
            service = ProfileMatchingService(db)
            await service.match_offer(offer_id)
        except Exception as e:
            logger.error("Background profile matching error for %s: %s", offer_id, e)
            db.rollback()
        finally:
            db.close()
