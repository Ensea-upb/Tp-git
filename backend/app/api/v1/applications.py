"""
Application endpoints — Sprint 6.

POST  /v1/applications              — créer une candidature + lancer génération LLM en fond
GET   /v1/applications              — lister toutes les candidatures
GET   /v1/applications/{id}         — détail d'une candidature
PATCH /v1/applications/{id}/status  — changer le statut
POST  /v1/applications/{id}/followup — planifier une relance
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
    FollowupCreate,
    FollowupOut,
)
from app.domain.errors import BusinessRuleError, NotFoundError
from app.infrastructure.db.session import get_db
from app.services.application_service import ApplicationService, populate_drafts_background

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ApplicationOut:
    try:
        app = ApplicationService(db).create(
            offer_id=payload.offer_id,
            source_channel=payload.source_channel,
            notes=payload.notes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    background_tasks.add_task(populate_drafts_background, app.id)
    return ApplicationOut.model_validate(app)


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)) -> list[ApplicationOut]:
    apps = ApplicationService(db).list_all()
    return [ApplicationOut.model_validate(a) for a in apps]


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(application_id: uuid.UUID, db: Session = Depends(get_db)) -> ApplicationOut:
    try:
        app = ApplicationService(db).get(application_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ApplicationOut.model_validate(app)


@router.patch("/{application_id}/status", response_model=ApplicationOut)
def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
) -> ApplicationOut:
    try:
        app = ApplicationService(db).update_status(application_id, payload.status)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ApplicationOut.model_validate(app)


@router.post(
    "/{application_id}/followup",
    response_model=FollowupOut,
    status_code=status.HTTP_201_CREATED,
)
def add_followup(
    application_id: uuid.UUID,
    payload: FollowupCreate,
    db: Session = Depends(get_db),
) -> FollowupOut:
    try:
        followup = ApplicationService(db).add_followup(
            application_id=application_id,
            scheduled_at=payload.scheduled_at,
            notes=payload.notes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return FollowupOut.model_validate(followup)
