"""Endpoints de gestion des préférences utilisateur (profil singleton)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import verify_api_key
from app.api.schemas.preferences import PreferencesOut, PreferencesUpdate
from app.infrastructure.db.session import get_db
from app.repositories.user_preference_repository import UserPreferenceRepository

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("", response_model=PreferencesOut, summary="Lire les préférences")
def get_preferences(db: Session = Depends(get_db)) -> PreferencesOut:
    """Retourne le profil de préférences (créé vide si inexistant)."""
    repo = UserPreferenceRepository(db)
    prefs = repo.get_or_create_default()
    db.commit()
    return PreferencesOut.model_validate(prefs)


@router.put("", response_model=PreferencesOut, summary="Mettre à jour les préférences")
def update_preferences(
    body: PreferencesUpdate,
    db: Session = Depends(get_db),
) -> PreferencesOut:
    """Remplace le profil de préférences (PUT complet)."""
    repo = UserPreferenceRepository(db)
    prefs = repo.get_or_create_default()

    # Mise à jour de tous les champs (PUT sémantique — remplacement total)
    prefs.preferred_contract_types = body.preferred_contract_types or None
    prefs.preferred_work_modes = body.preferred_work_modes or None
    prefs.preferred_locations = body.preferred_locations or None
    prefs.preferred_keywords = body.preferred_keywords or None
    prefs.preferred_domains = body.preferred_domains or None
    prefs.exclude_keywords = body.exclude_keywords or None
    prefs.minimum_duration_months = body.minimum_duration_months

    repo.save(prefs)
    db.commit()
    db.refresh(prefs)
    return PreferencesOut.model_validate(prefs)
