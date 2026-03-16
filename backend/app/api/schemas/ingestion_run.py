import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.api.schemas.source import SourceOut


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    offers_fetched: int
    offers_created: int
    offers_updated: int
    offers_duplicated: int
    offers_failed: int
    error_summary: str | None = None
    created_at: datetime

    source: SourceOut | None = None


class PaginatedIngestionRuns(BaseModel):
    items: list[IngestionRunOut]
    total: int
    page: int
    page_size: int
    has_next: bool
