"""
Application endpoints — Sprint 7 + Sprint 9.

POST  /v1/applications                           — créer + lancer génération LLM
GET   /v1/applications?status=&page=&limit=      — liste paginée avec filtre
GET   /v1/applications/stats                     — statistiques agrégées (Sprint 9)
GET   /v1/applications/{id}                      — détail
PATCH /v1/applications/{id}/status               — transition machine d'états
POST  /v1/applications/{id}/followup             — planifier une relance
GET   /v1/applications/{id}/timeline             — historique événements (Sprint 9)
POST  /v1/applications/{id}/recruiter-reply      — réponse recruteur (Sprint 9)
GET   /v1/applications/{id}/followup-recommendation — recommandation délai (Sprint 9)
POST  /v1/applications/{id}/interview-prep       — préparation entretien contextuelle (Sprint 9)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.application import (
    ApplicationCreate,
    ApplicationEventOut,
    ApplicationOut,
    ApplicationStatsOut,
    ApplicationStatusUpdate,
    FollowupCreate,
    FollowupOut,
    FollowupRecommendationOut,
    PaginatedApplications,
    RecruiterReplyCreate,
)
from app.domain.enums.application_status import ApplicationStatus
from app.domain.errors import BusinessRuleError, NotFoundError
from app.infrastructure.db.session import get_db
from app.services.application_service import ApplicationService, populate_drafts_background
from app.services.followup_recommendation_service import FollowupRecommendationService
from app.services.interview_preparation_service import InterviewPreparationService

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
    dependencies=[Depends(verify_api_key)],
)


# ── Sprint 9 : stats doit être avant /{id} pour ne pas être capturé ───────────


@router.get("/stats", response_model=ApplicationStatsOut, summary="Statistiques des candidatures")
def get_stats(db: Session = Depends(get_db)) -> ApplicationStatsOut:
    stats = ApplicationService(db).get_stats()
    return ApplicationStatsOut(**stats)


# ── Sprint 7 ──────────────────────────────────────────────────────────────────


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


# ── Sprint 9 : Timeline ──────────────────────────────────────────────────────


@router.get("/{application_id}/timeline", response_model=list[ApplicationEventOut])
def get_timeline(
    application_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[ApplicationEventOut]:
    try:
        events = ApplicationService(db).get_timeline(application_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [ApplicationEventOut.model_validate(e) for e in events]


# ── Sprint 9 : Réponse recruteur ─────────────────────────────────────────────


@router.post(
    "/{application_id}/recruiter-reply",
    response_model=ApplicationEventOut,
    status_code=status.HTTP_201_CREATED,
)
def add_recruiter_reply(
    application_id: uuid.UUID,
    payload: RecruiterReplyCreate,
    db: Session = Depends(get_db),
) -> ApplicationEventOut:
    try:
        event = ApplicationService(db).add_recruiter_reply(
            application_id=application_id,
            message_text=payload.message_text,
            channel=payload.channel,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ApplicationEventOut.model_validate(event)


# ── Sprint 9 : Recommandation de délai de suivi ──────────────────────────────


@router.get(
    "/{application_id}/followup-recommendation",
    response_model=FollowupRecommendationOut,
)
def get_followup_recommendation(
    application_id: uuid.UUID, db: Session = Depends(get_db)
) -> FollowupRecommendationOut:
    try:
        app = ApplicationService(db).get(application_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    recommendation = FollowupRecommendationService().recommend(app)
    return FollowupRecommendationOut(**recommendation)


# ── Sprint 9 : Préparation entretien contextuelle ────────────────────────────


@router.post("/{application_id}/interview-prep")
async def get_interview_prep(
    application_id: uuid.UUID, db: Session = Depends(get_db)
) -> dict:
    try:
        app = ApplicationService(db).get(application_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    service = InterviewPreparationService(db)
    return await service.prepare(app)
