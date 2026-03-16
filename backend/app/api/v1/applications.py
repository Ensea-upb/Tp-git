"""
Application endpoints — Sprint 7.

POST  /v1/applications                    — créer + lancer génération LLM
GET   /v1/applications?status=&page=&limit= — liste paginée avec filtre
GET   /v1/applications/{id}               — détail
PATCH /v1/applications/{id}/status        — transition machine d'états
POST  /v1/applications/{id}/followup      — planifier une relance
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
    FollowupCreate,
    FollowupOut,
    PaginatedApplications,
)
from app.domain.enums.application_status import ApplicationStatus
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


@router.get("", response_model=PaginatedApplications)
def list_applications(
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> PaginatedApplications:
    items, total = ApplicationService(db).list_paginated(
        status=status_filter, page=page, limit=limit
    )
    return PaginatedApplications(
        items=[ApplicationOut.model_validate(a) for a in items],
        total=total,
        page=page,
        limit=limit,
        has_next=(page * limit) < total,
    )


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
