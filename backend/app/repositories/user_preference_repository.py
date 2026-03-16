"""
Repository pour le profil de préférences utilisateur (singleton).

Pattern : get_or_create_default() — crée le profil par défaut s'il n'existe pas encore.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models.user_preference import DEFAULT_PROFILE_ID, UserPreference


class UserPreferenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_default(self) -> UserPreference | None:
        return self.db.execute(
            select(UserPreference).where(UserPreference.id == DEFAULT_PROFILE_ID)
        ).scalar_one_or_none()

    def get_or_create_default(self) -> UserPreference:
        prefs = self.get_default()
        if prefs is None:
            prefs = UserPreference(id=DEFAULT_PROFILE_ID)
            self.db.add(prefs)
            self.db.flush()
        return prefs

    def save(self, prefs: UserPreference) -> UserPreference:
        self.db.flush()
        return prefs
