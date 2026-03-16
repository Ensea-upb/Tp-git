"""
SkillGapService — Sprint 10.

Compare les compétences du candidat (profil) avec les compétences requises
par une offre (tags + analyse LLM) et retourne la liste des compétences manquantes.

Sources des compétences candidate :
  - CandidateProfile.skills
  - CandidateProfile.tech_stack

Sources des compétences requises (offre) :
  - Offer.tags
  - OfferLLMAnalysis.skills_required
  - OfferLLMAnalysis.tech_stack

Toutes les comparaisons sont insensibles à la casse.
"""
from sqlalchemy.orm import Session

from app.infrastructure.db.models.candidate_profile import CandidateProfile
from app.infrastructure.db.models.offer import Offer
from app.repositories.candidate_profile_repository import CandidateProfileRepository


class SkillGapService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._profile: CandidateProfile | None = None

    # ── Interface publique ─────────────────────────────────────────────

    def analyze_for_offer(self, offer: Offer) -> list[str]:
        """
        Retourne les compétences requises par l'offre absentes du profil candidat.
        Résultat trié alphabétiquement.

        Retourne [] si le profil est absent ou ne déclare aucune compétence :
        un profil vide rendrait toutes les compétences "manquantes", ce qui
        produirait un signal trop bruyant et inexploitable.
        """
        profile = self._get_profile()
        candidate_skills = _extract_candidate_skills(profile)
        if not candidate_skills:
            return []
        required_skills = _extract_required_skills(offer)
        missing = required_skills - candidate_skills
        return sorted(missing)

    def analyze_for_offers(self, offers: list[Offer]) -> list[dict]:
        """
        Retourne les skill gaps pour une liste d'offres.
        N'inclut que les offres avec au moins une compétence manquante.

        Chaque élément : {"offer_id", "offer_title", "missing_skills"}
        """
        results = []
        for offer in offers:
            missing = self.analyze_for_offer(offer)
            if missing:
                results.append({
                    "offer_id": offer.id,
                    "offer_title": offer.normalized_title,
                    "missing_skills": missing,
                })
        return results

    # ── Interne ───────────────────────────────────────────────────────

    def _get_profile(self) -> CandidateProfile | None:
        if self._profile is None:
            self._profile = CandidateProfileRepository(self.db).get_default()
        return self._profile


# ── Helpers (fonctions pures) ─────────────────────────────────────────────────


def _extract_candidate_skills(profile: CandidateProfile | None) -> set[str]:
    """Collecte et normalise toutes les compétences déclarées par le candidat."""
    skills: set[str] = set()
    if profile is None:
        return skills
    for field_val in (profile.skills, profile.tech_stack):
        if field_val:
            skills.update(s.strip().lower() for s in field_val if isinstance(s, str) and s.strip())
    return skills


def _extract_required_skills(offer: Offer) -> set[str]:
    """Collecte et normalise les compétences requises par l'offre."""
    required: set[str] = set()
    if offer.tags:
        required.update(t.strip().lower() for t in offer.tags if isinstance(t, str) and t.strip())
    analysis = getattr(offer, "llm_analysis", None)
    if analysis is not None:
        for field_val in (analysis.skills_required, analysis.tech_stack):
            if field_val:
                required.update(
                    s.strip().lower() for s in field_val if isinstance(s, str) and s.strip()
                )
    return required
