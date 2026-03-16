from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict


class OfferLLMAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: uuid.UUID
    model_used: str
    summary: Optional[str] = None
    missions: Optional[list[str]] = None
    skills_required: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    seniority_level: Optional[str] = None
    analysis_status: str
    analyzed_at: datetime
    updated_at: datetime


class ProfileMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: uuid.UUID
    model_used: str
    match_score: Optional[float] = None
    strengths: Optional[list[str]] = None
    gaps: Optional[list[str]] = None
    recommendation: Optional[str] = None
    match_status: str
    matched_at: datetime
    updated_at: datetime
