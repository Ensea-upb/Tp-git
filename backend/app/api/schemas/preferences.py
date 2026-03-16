import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    preferred_contract_types: list[str] | None = None
    preferred_work_modes: list[str] | None = None
    preferred_locations: list[str] | None = None
    preferred_keywords: list[str] | None = None
    preferred_domains: list[str] | None = None
    exclude_keywords: list[str] | None = None
    minimum_duration_months: int | None = None
    created_at: datetime
    updated_at: datetime


class PreferencesUpdate(BaseModel):
    """Remplacement complet du profil (PUT sémantique).
    Un champ absent est remis à None — envoyer [] pour vider une liste."""

    preferred_contract_types: list[str] | None = None
    preferred_work_modes: list[str] | None = None
    preferred_locations: list[str] | None = None
    preferred_keywords: list[str] | None = None
    preferred_domains: list[str] | None = None
    exclude_keywords: list[str] | None = None
    minimum_duration_months: int | None = None
