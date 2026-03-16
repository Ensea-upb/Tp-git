import uuid

from pydantic import BaseModel

from app.domain.enums.strategy_action_type import StrategyActionType


class StrategyActionOut(BaseModel):
    action_type: StrategyActionType
    reason: str
    priority: int
    application_id: uuid.UUID | None = None
    offer_id: uuid.UUID | None = None


class PrioritizedOfferOut(BaseModel):
    offer_id: uuid.UUID
    title: str
    priority_score: float
    ranking_score: float | None
    matching_score: float | None
    location_text: str | None = None
    company_name: str | None = None


class SkillGapOut(BaseModel):
    offer_id: uuid.UUID
    offer_title: str
    missing_skills: list[str]


class StrategyRecommendationsOut(BaseModel):
    actions: list[StrategyActionOut]
    prioritized_offers: list[PrioritizedOfferOut]
    skill_gaps: list[SkillGapOut]
