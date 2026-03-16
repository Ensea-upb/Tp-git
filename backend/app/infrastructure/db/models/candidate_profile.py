import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base

DEFAULT_CANDIDATE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    school: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tech_stack: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    languages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    experiences: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    projects: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_domains: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    availability: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
