import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class IngestionRun(Base):
    """Trace une exécution d'ingestion pour un source donné."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Nullable pour les runs "toutes sources"
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="RUNNING", index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    offers_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offers_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offers_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offers_duplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offers_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relation
    source: Mapped["Source | None"] = relationship("Source")  # noqa: F821
