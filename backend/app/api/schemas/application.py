import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums.application_status import ApplicationStatus


class ApplicationCreate(BaseModel):
    offer_id: uuid.UUID
    source_channel: str | None = None
    notes: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class FollowupCreate(BaseModel):
    scheduled_at: datetime
    notes: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("scheduled_at must be strictly in the future")
        return v


class FollowupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    scheduled_at: datetime
    sent_at: datetime | None = None
    status: str
    notes: str | None = None
    created_at: datetime


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    status: ApplicationStatus
    applied_at: datetime | None = None
    source_channel: str | None = None
    drafts_ready: bool = False
    draft_cover_letter: str | None = None
    draft_email: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    followups: list[FollowupOut] = []

    # Champs enrichis depuis l'offre liée (via ORM property)
    offer_title: str | None = None
    offer_source_name: str | None = None


class PaginatedApplications(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int
    limit: int
    has_next: bool


# ── Sprint 9 : Timeline ──────────────────────────────────────────────


class ApplicationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    event_type: str
    payload_json: dict | None = None
    created_at: datetime


# ── Sprint 9 : Réponse recruteur ─────────────────────────────────────


class RecruiterReplyCreate(BaseModel):
    message_text: str = Field(min_length=1, max_length=5000)
    channel: Literal["email", "phone", "linkedin", "other"] | None = None


# ── Sprint 9 : Recommandation de suivi ───────────────────────────────


class FollowupRecommendationOut(BaseModel):
    recommended_delay_days: int
    reason: str
    suggested_date: datetime


# ── Sprint 9 : Statistiques ──────────────────────────────────────────


class ApplicationStatsOut(BaseModel):
    total: int
    interviews: int
    rejections: int
    offers: int
    response_rate: float
