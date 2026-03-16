import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.offer import Offer


class OfferLLMAnalysis(Base):
    __tablename__ = "offer_llm_analyses"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    missions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    skills_required: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tech_stack: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    seniority_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="PENDING"
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    offer: Mapped["Offer"] = relationship("Offer", back_populates="llm_analysis")
