import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    base_url: str | None = None
    is_active: bool
    check_frequency_hours: int
    legal_status: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceCreate(BaseModel):
    name: str
    source_type: str
    base_url: str | None = None
    is_active: bool = True
    check_frequency_hours: int = 3
    legal_status: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    is_active: bool | None = None
    check_frequency_hours: int | None = None
    legal_status: str | None = None
