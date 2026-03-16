import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums.application_status import ApplicationStatus
from app.infrastructure.db.base import Base


class Application(Base):
    """Candidature liée à une offre — Sprint 6."""

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        String(50), nullable=False, default=ApplicationStatus.DRAFT, index=True
    )

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Brouillons générés par LLM
    drafts_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    draft_cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_email: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations
    offer: Mapped["Offer | None"] = relationship("Offer")  # noqa: F821
    followups: Mapped[list["ApplicationFollowup"]] = relationship(  # noqa: F821
        "ApplicationFollowup",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationFollowup.scheduled_at",
    )

    # ── Champs calculés exposés via Pydantic from_attributes ──────────

    @property
    def offer_title(self) -> str | None:
        return self.offer.normalized_title if self.offer else None

    @property
    def offer_source_name(self) -> str | None:
        if self.offer and self.offer.primary_source:
            return self.offer.primary_source.name
        return None
