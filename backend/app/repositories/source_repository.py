import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models.source import Source


class SourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_active(self) -> list[Source]:
        result = self.db.execute(select(Source).where(Source.is_active == True))  # noqa: E712
        return list(result.scalars().all())

    def get_by_id(self, source_id: uuid.UUID) -> Source | None:
        return self.db.execute(select(Source).where(Source.id == source_id)).scalar_one_or_none()

    def get_by_name(self, name: str) -> Source | None:
        return self.db.execute(select(Source).where(Source.name == name)).scalar_one_or_none()

    def create(self, source: Source) -> Source:
        self.db.add(source)
        self.db.flush()
        return source
