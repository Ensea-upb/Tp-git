import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Text, DateTime, Numeric, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.offer import Offer


class ProfileMatchLLM(Base):
    __tablename__ = "profile_match_llm"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    gaps: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="PENDING"
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    offer: Mapped["Offer"] = relationship("Offer", back_populates="profile_match")
