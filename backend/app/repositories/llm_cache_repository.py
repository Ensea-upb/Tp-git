from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.db.models.llm_cache import LLMCache


class LLMCacheRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, cache_key: str) -> str | None:
        row = self.db.execute(
            select(LLMCache).where(LLMCache.cache_key == cache_key)
        ).scalar_one_or_none()
        return row.response_text if row else None

    def set(self, cache_key: str, model: str, prompt: str, response_text: str) -> None:
        existing = self.db.execute(
            select(LLMCache).where(LLMCache.cache_key == cache_key)
        ).scalar_one_or_none()
        if existing:
            existing.response_text = response_text
        else:
            self.db.add(LLMCache(
                cache_key=cache_key,
                model=model,
                prompt_hash=cache_key,
                response_text=response_text,
            ))
        # Caller flushes / commits
