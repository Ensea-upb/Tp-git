"""
InterviewPreparationService — Préparation d'entretien contextuelle (Sprint 9).

Enrichit le prompt LLM avec :
- la description complète de l'offre
- les compétences requises (depuis OfferLLMAnalysis si disponible)
- le profil candidat
- l'historique de la candidature (events timeline)
"""
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.db.models.application import Application
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.candidate_profile_repository import CandidateProfileRepository
from app.repositories.offer_llm_analysis_repository import OfferLLMAnalysisRepository
from app.repositories.offer_repository import OfferRepository
from app.services.llm.llm_service import call_llm_json
from app.services.llm.prompt_builder import build_contextual_interview_prep_prompt

logger = logging.getLogger(__name__)


class InterviewPreparationService:
    def __init__(self, db: Session):
        self.db = db
        self.offer_repo = OfferRepository(db)
        self.profile_repo = CandidateProfileRepository(db)
        self.analysis_repo = OfferLLMAnalysisRepository(db)
        self.event_repo = ApplicationEventRepository(db)

    async def prepare(self, application: Application) -> dict:
        """
        Génère une préparation d'entretien contextuelle.
        Retourne un dict (non persisté).
        """
        offer = self.offer_repo.get_by_id(application.offer_id)
        if offer is None:
            return {"error": f"Offer {application.offer_id} not found"}

        profile = self.profile_repo.get_default()
        if profile is None:
            return {"error": "No candidate profile found. Create one at /v1/candidate first."}

        # Compétences requises depuis l'analyse LLM (enrichissement optionnel)
        skills_required: list[str] | None = None
        analysis = self.analysis_repo.get(application.offer_id)
        if analysis and analysis.analysis_status == "DONE":
            skills_required = analysis.skills_required or None

        # Historique de la candidature
        events = self.event_repo.get_timeline(application.id)
        history = [
            {
                "event_type": e.event_type,
                "created_at": e.created_at.isoformat() if e.created_at else "",
                "detail": _event_detail(e),
            }
            for e in events
        ]

        prompt = build_contextual_interview_prep_prompt(
            offer=offer,
            profile=profile,
            application_history=history,
            skills_required=skills_required,
        )

        result = await call_llm_json(
            prompt=prompt,
            model=settings.llm_model_hq,
            max_tokens=800,
            temperature=0.2,
            db_session=self.db,
        )
        self.db.commit()
        return result or {"error": "LLM did not return valid JSON"}


def _event_detail(event) -> str:
    """Extrait un libellé lisible depuis le payload d'un événement."""
    payload = event.payload_json or {}
    event_type = event.event_type

    if event_type == "STATUS_CHANGED":
        return f"{payload.get('from', '?')} → {payload.get('to', '?')}"
    if event_type == "RECRUITER_REPLIED":
        msg = (payload.get("message_text") or "")[:80]
        channel = payload.get("channel") or "?"
        return f"[{channel}] {msg}"
    if event_type == "FOLLOWUP_SCHEDULED":
        return f"Relance prévue le {payload.get('scheduled_at', '?')}"
    if event_type == "DRAFTS_READY":
        return "Brouillons générés"
    if event_type == "APPLICATION_CREATED":
        return "Candidature créée"
    return str(payload)[:60]
