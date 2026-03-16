import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.db.models.offer_llm_analysis import OfferLLMAnalysis


class OfferLLMAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, offer_id: uuid.UUID) -> OfferLLMAnalysis | None:
        return self.db.execute(
            select(OfferLLMAnalysis).where(OfferLLMAnalysis.offer_id == offer_id)
        ).scalar_one_or_none()

    def upsert(self, analysis: OfferLLMAnalysis) -> OfferLLMAnalysis:
        existing = self.get(analysis.offer_id)
        if existing:
            existing.model_used = analysis.model_used
            existing.summary = analysis.summary
            existing.missions = analysis.missions
            existing.skills_required = analysis.skills_required
            existing.tech_stack = analysis.tech_stack
            existing.seniority_level = analysis.seniority_level
            existing.raw_response = analysis.raw_response
            existing.analysis_status = analysis.analysis_status
            self.db.flush()
            return existing
        self.db.add(analysis)
        self.db.flush()
        return analysis
