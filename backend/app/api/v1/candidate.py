"""
Candidate profile endpoints.
GET /v1/candidate   — get singleton profile
PUT /v1/candidate   — upsert singleton profile
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.db.session import get_db
from app.api.schemas.candidate import CandidateProfileOut, CandidateProfileUpdate
from app.repositories.candidate_profile_repository import CandidateProfileRepository

router = APIRouter(prefix="/candidate", tags=["candidate"])


@router.get("", response_model=CandidateProfileOut)
def get_candidate_profile(db: Session = Depends(get_db)):
    repo = CandidateProfileRepository(db)
    profile = repo.get_or_create_default()
    db.commit()
    return profile


@router.put("", response_model=CandidateProfileOut)
def update_candidate_profile(
    payload: CandidateProfileUpdate,
    db: Session = Depends(get_db),
):
    repo = CandidateProfileRepository(db)
    profile = repo.get_or_create_default()

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    repo.save(profile)
    db.commit()
    db.refresh(profile)
    return profile
