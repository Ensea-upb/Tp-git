"""
Offer LLM Analysis Service.
Analyzes an offer with a local LLM (Ollama) and stores structured results.
LLM failures are caught and stored as FAILED status — never breaks ingestion.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis
from app.repositories.offer_llm_analysis_repository import OfferLLMAnalysisRepository
from app.repositories.offer_repository import OfferRepository
from app.services.llm.llm_service import call_llm_json
from app.services.llm.prompt_builder import build_offer_analysis_prompt

logger = logging.getLogger(__name__)


class OfferLLMAnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.offer_repo = OfferRepository(db)
        self.analysis_repo = OfferLLMAnalysisRepository(db)

    async def analyze_offer(self, offer_id: uuid.UUID) -> OfferLLMAnalysis:
        """
        Analyze a single offer with the LLM.
        Creates or updates offer_llm_analyses row.
        """
        offer = self.offer_repo.get_by_id(offer_id)
        if offer is None:
            raise ValueError(f"Offer {offer_id} not found")

        model = settings.llm_model_default
        prompt = build_offer_analysis_prompt(offer)

        analysis = OfferLLMAnalysis(
            offer_id=offer_id,
            model_used=model,
            analysis_status="RUNNING",
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
                analysis.summary = parsed.get("summary")
                analysis.missions = parsed.get("missions")
                analysis.skills_required = parsed.get("skills_required")
                analysis.tech_stack = parsed.get("tech_stack")
                analysis.seniority_level = parsed.get("seniority_level")
                analysis.analysis_status = "DONE"
            else:
                analysis.analysis_status = "FAILED"
                analysis.raw_response = str(parsed)
        except Exception as e:
            logger.error("LLM analysis failed for offer %s: %s", offer_id, e)
            analysis.analysis_status = "FAILED"
            analysis.raw_response = str(e)

        result = self.analysis_repo.upsert(analysis)
        self.db.commit()
        return result

    async def analyze_offer_background(self, offer_id: uuid.UUID) -> None:
        """Background-safe wrapper: creates its own session."""
        from app.infrastructure.db.session import SessionLocal
        db = SessionLocal()
        try:
            service = OfferLLMAnalysisService(db)
            await service.analyze_offer(offer_id)
        except Exception as e:
            logger.error("Background LLM analysis error for %s: %s", offer_id, e)
            db.rollback()
        finally:
            db.close()
