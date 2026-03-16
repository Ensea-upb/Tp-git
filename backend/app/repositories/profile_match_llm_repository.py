import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.db.models.profile_match_llm import ProfileMatchLLM


class ProfileMatchLLMRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, offer_id: uuid.UUID) -> ProfileMatchLLM | None:
        return self.db.execute(
            select(ProfileMatchLLM).where(ProfileMatchLLM.offer_id == offer_id)
        ).scalar_one_or_none()

    def upsert(self, match: ProfileMatchLLM) -> ProfileMatchLLM:
        existing = self.get(match.offer_id)
        if existing:
            existing.model_used = match.model_used
            existing.match_score = match.match_score
            existing.strengths = match.strengths
            existing.gaps = match.gaps
            existing.recommendation = match.recommendation
            existing.raw_response = match.raw_response
            existing.match_status = match.match_status
            self.db.flush()
            return existing
        self.db.add(match)
        self.db.flush()
        return match
