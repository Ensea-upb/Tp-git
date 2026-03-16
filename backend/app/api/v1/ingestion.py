import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.ingestion_run import IngestionRunOut, PaginatedIngestionRuns
from app.infrastructure.db.session import get_db
from app.repositories.ingestion_run_repository import IngestionRunRepository
from app.services.offer_ingestion_service import OfferIngestionService

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post(
    "/run",
    response_model=list[IngestionRunOut],
    status_code=status.HTTP_200_OK,
    summary="Déclencher une ingestion",
)
def trigger_ingestion(
    source_id: uuid.UUID | None = Query(
        default=None,
        description="UUID de la source à ingérer. Omis = toutes les sources actives.",
    ),
    db: Session = Depends(get_db),
) -> list[IngestionRunOut]:
    """
    Déclenche l'ingestion de manière synchrone.
    Retourne la liste des runs créés avec leur bilan.

    Note : opération synchrone. Pour des pipelines longs, préférer
    un worker asynchrone (Sprint 4).
    """
    service = OfferIngestionService(db)
    run_repo = IngestionRunRepository(db)

    if source_id:
        result = service.run_source(source_id)
        results = [result]
    else:
        results = service.run_all()

    # Récupérer les runs créés
    run_ids = [r.run_id for r in results if r.run_id is not None]
    runs = [run_repo.get_by_id(rid) for rid in run_ids if rid]
    return [IngestionRunOut.model_validate(r) for r in runs if r]


@router.get(
    "/runs",
    response_model=PaginatedIngestionRuns,
    summary="Historique des runs d'ingestion",
)
def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_id: uuid.UUID | None = Query(default=None, description="Filtrer par source"),
    db: Session = Depends(get_db),
) -> PaginatedIngestionRuns:
    repo = IngestionRunRepository(db)
    runs, total = repo.get_all(page=page, page_size=page_size, source_id=source_id)
    return PaginatedIngestionRuns(
        items=[IngestionRunOut.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get(
    "/runs/{run_id}",
    response_model=IngestionRunOut,
    summary="Détail d'un run d'ingestion",
)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> IngestionRunOut:
    repo = IngestionRunRepository(db)
    run = repo.get_by_id(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IngestionRun {run_id} introuvable.",
        )
    return IngestionRunOut.model_validate(run)
