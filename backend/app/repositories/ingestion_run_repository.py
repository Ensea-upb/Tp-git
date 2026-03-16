import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.dto.ingestion_result import IngestionResult
from app.domain.enums.ingestion_status import IngestionStatus
from app.infrastructure.db.models.ingestion_run import IngestionRun


class IngestionRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Lecture                                                              #
    # ------------------------------------------------------------------ #

    def get_by_id(self, run_id: uuid.UUID) -> IngestionRun | None:
        return self.db.execute(
            select(IngestionRun)
            .options(joinedload(IngestionRun.source))
            .where(IngestionRun.id == run_id)
        ).scalar_one_or_none()

    def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        source_id: uuid.UUID | None = None,
    ) -> tuple[list[IngestionRun], int]:
        from sqlalchemy import func

        query = (
            select(IngestionRun)
            .options(joinedload(IngestionRun.source))
            .order_by(IngestionRun.started_at.desc())
        )
        count_query = select(func.count(IngestionRun.id))

        if source_id is not None:
            query = query.where(IngestionRun.source_id == source_id)
            count_query = count_query.where(IngestionRun.source_id == source_id)

        total = self.db.execute(count_query).scalar_one()
        offset = (page - 1) * page_size
        runs = list(
            self.db.execute(query.offset(offset).limit(page_size)).scalars().unique()
        )
        return runs, total

    # ------------------------------------------------------------------ #
    # Écriture                                                             #
    # ------------------------------------------------------------------ #

    def create_running(self, source_id: uuid.UUID | None) -> IngestionRun:
        """Crée un run en état RUNNING avec started_at=now()."""
        run = IngestionRun(
            id=uuid.uuid4(),
            source_id=source_id,
            status=IngestionStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish(
        self,
        run: IngestionRun,
        result: IngestionResult,
        status: IngestionStatus,
    ) -> None:
        """Met à jour le run avec les résultats finaux."""
        run.status = status
        run.finished_at = datetime.now(tz=timezone.utc)
        run.offers_fetched = result.total_fetched
        run.offers_created = result.new_offers
        run.offers_updated = result.updated_offers
        run.offers_duplicated = result.duplicates
        run.offers_failed = result.errors
        if result.error_details:
            run.error_summary = "; ".join(result.error_details[:5])
        self.db.flush()
