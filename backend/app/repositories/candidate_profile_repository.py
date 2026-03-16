import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.db.models.candidate_profile import CandidateProfile, DEFAULT_CANDIDATE_ID


class CandidateProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_default(self) -> CandidateProfile | None:
        return self.db.execute(
            select(CandidateProfile).where(CandidateProfile.id == DEFAULT_CANDIDATE_ID)
        ).scalar_one_or_none()

    def get_or_create_default(self) -> CandidateProfile:
        profile = self.get_default()
        if profile is None:
            profile = CandidateProfile(id=DEFAULT_CANDIDATE_ID)
            self.db.add(profile)
            self.db.flush()
        return profile

    def save(self, profile: CandidateProfile) -> CandidateProfile:
        self.db.flush()
        return profile
