import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class OfferRaw(Base):
    """Offre telle que collectée par un connecteur, avant normalisation."""

    __tablename__ = "offers_raw"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True
    )

    # Identifiants externes
    external_offer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer_url: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)

    # Contenu brut
    raw_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_company_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dates
    published_at_detected: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Déduplication et traitement
    checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations
    source: Mapped["Source"] = relationship("Source")  # noqa: F821
    normalized_offer: Mapped["Offer | None"] = relationship(  # noqa: F821
        "Offer", back_populates="raw_offer", foreign_keys="Offer.raw_offer_id"
    )
