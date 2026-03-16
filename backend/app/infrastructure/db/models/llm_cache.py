import uuid
from datetime import datetime

from sqlalchemy import Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class LLMCache(Base):
    __tablename__ = "llm_cache"

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
