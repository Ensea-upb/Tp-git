"""
Profil de préférences utilisateur — singleton.

Un seul enregistrement dans cette table (id = DEFAULT_PROFILE_ID).
Accès via UserPreferenceRepository.get_or_create_default().
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base

# UUID fixe du profil par défaut (mono-utilisateur)
DEFAULT_PROFILE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=lambda: DEFAULT_PROFILE_ID
    )

    # Contrats préférés (ex. ["Stage", "Alternance"])
    preferred_contract_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    # Modes de travail (ex. ["REMOTE", "HYBRID"])
    preferred_work_modes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    # Localisations (ex. ["Paris", "Île-de-France"])
    preferred_locations: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    # Mots-clés positifs dans titre/description
    preferred_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    # Domaines tags (ex. ["data", "ml", "ai"])
    preferred_domains: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    # Mots-clés à exclure/pénaliser
    exclude_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    # Durée minimale souhaitée
    minimum_duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
