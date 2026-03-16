import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
    draft_cover_letter: str | None = None
    draft_email: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    followups: list[FollowupOut] = []
