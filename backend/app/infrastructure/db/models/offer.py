import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.offer_state import OfferState
from app.domain.enums.work_mode import WorkMode
from app.infrastructure.db.base import Base


class Offer(Base):
    """Offre normalisée — table principale du Sprint 1."""

    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Traçabilité vers l'offre brute d'origine
    raw_offer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers_raw.id"), nullable=True, index=True
    )

    # Relations
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    )
    primary_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True, index=True
    )

    # Contenu
    normalized_title: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[WorkMode | None] = mapped_column(String(50), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Dates
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # État métier
    current_state: Mapped[OfferState] = mapped_column(
        String(50), nullable=False, default=OfferState.DETECTED, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Scoring
    global_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # DEPRECATED: action_score n'est plus écrit par aucun service. Colonne à supprimer via migration 006.
    action_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_justification: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Scoring personnalisé (calculé depuis les préférences utilisateur)
    personalized_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    personalized_justification: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Tags métier (data, ml, ai, analytics, econometrics…)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Déduplication
    offer_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, unique=True)
    external_offer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    semantic_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Métadonnées
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations ORM
    company: Mapped["Company | None"] = relationship("Company", back_populates="offers")  # noqa: F821
    primary_source: Mapped["Source | None"] = relationship("Source", back_populates="offers")  # noqa: F821
    raw_offer: Mapped["OfferRaw | None"] = relationship(  # noqa: F821
        "OfferRaw", back_populates="normalized_offer", foreign_keys=[raw_offer_id]
    )
    user_status: Mapped["OfferUserStatus | None"] = relationship(  # noqa: F821
        "OfferUserStatus", back_populates="offer", uselist=False, cascade="all, delete-orphan"
    )
    llm_analysis: Mapped["OfferLLMAnalysis | None"] = relationship(  # noqa: F821
        "OfferLLMAnalysis", back_populates="offer", uselist=False, cascade="all, delete-orphan"
    )
    profile_match: Mapped["ProfileMatchLLM | None"] = relationship(  # noqa: F821
        "ProfileMatchLLM", back_populates="offer", uselist=False, cascade="all, delete-orphan"
    )
