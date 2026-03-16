"""
Statut utilisateur sur une offre — un statut exclusif par offre.

Statuts : FAVORITE, SHORTLISTED, REJECTED, APPLIED
La table a offer_id comme PK : un seul enregistrement par offre.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.user_status import UserStatus
from app.infrastructure.db.base import Base


class OfferUserStatus(Base):
    __tablename__ = "offer_user_statuses"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
        primary_key=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )

    # Notes libres optionnelles (utiles plus tard)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relation vers Offer (lecture seule)
    offer: Mapped["Offer | None"] = relationship("Offer", back_populates="user_status")  # noqa: F821
