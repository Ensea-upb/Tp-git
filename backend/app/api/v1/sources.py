import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.source import SourceCreate, SourceOut, SourceUpdate
from app.infrastructure.db.models.source import Source
from app.infrastructure.db.session import get_db
from app.repositories.source_repository import SourceRepository

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[SourceOut], summary="Liste de toutes les sources")
def list_sources(db: Session = Depends(get_db)) -> list[SourceOut]:
    repo = SourceRepository(db)
    sources = db.execute(
        __import__("sqlalchemy").select(Source).order_by(Source.name)
    ).scalars().all()
    return [SourceOut.model_validate(s) for s in sources]


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED, summary="Créer une source")
def create_source(body: SourceCreate, db: Session = Depends(get_db)) -> SourceOut:
    repo = SourceRepository(db)
    existing = repo.get_by_name(body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Une source nommée '{body.name}' existe déjà.",
        )
    source = Source(
        id=uuid.uuid4(),
        name=body.name,
        source_type=body.source_type,
        base_url=body.base_url,
        is_active=body.is_active,
        check_frequency_hours=body.check_frequency_hours,
        legal_status=body.legal_status,
    )
    repo.create(source)
    db.commit()
    db.refresh(source)
    return SourceOut.model_validate(source)


@router.patch("/{source_id}", response_model=SourceOut, summary="Mettre à jour une source")
def update_source(
    source_id: uuid.UUID,
    body: SourceUpdate,
    db: Session = Depends(get_db),
) -> SourceOut:
    repo = SourceRepository(db)
    source = repo.get_by_id(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} introuvable.",
        )
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)
    db.flush()
    db.commit()
    db.refresh(source)
    return SourceOut.model_validate(source)
