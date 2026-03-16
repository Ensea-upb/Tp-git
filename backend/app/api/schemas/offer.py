import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode


class CompanyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sector: str | None = None
    main_location: str | None = None


class SourceBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str


class OfferOut(BaseModel):
    """Schéma de sortie complet d'une offre normalisée."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    normalized_title: str
    normalized_description: str | None = None
    contract_type: str | None = None
    duration_months: int | None = None
    location_text: str | None = None
    work_mode: WorkMode | None = None
    education_level: str | None = None
    published_at: datetime | None = None
    deadline_at: datetime | None = None
    current_state: OfferState
    is_active: bool
    global_score: float | None = None
    action_score: float | None = None
    score_justification: dict | None = None
    offer_url: str | None = None
    created_at: datetime
    updated_at: datetime

    # Relations
    company: CompanyBrief | None = None
    primary_source: SourceBrief | None = None


class OfferListItem(BaseModel):
    """Schéma allégé pour la liste des offres."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    normalized_title: str
    contract_type: str | None = None
    duration_months: int | None = None
    location_text: str | None = None
    work_mode: WorkMode | None = None
    current_state: OfferState
    global_score: float | None = None
    action_score: float | None = None
    published_at: datetime | None = None
    created_at: datetime

    company: CompanyBrief | None = None
    primary_source: SourceBrief | None = None


class PaginatedOffers(BaseModel):
    """Réponse paginée — format standard V2."""

    items: list[OfferListItem]
    total: int
    page: int
    page_size: int
    has_next: bool
