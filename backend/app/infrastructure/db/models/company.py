import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    main_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # cible / neutre / exclue
    company_status: Mapped[str] = mapped_column(String(50), default="neutre", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="company")  # noqa: F821
