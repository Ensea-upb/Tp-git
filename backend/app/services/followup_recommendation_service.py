"""
FollowupRecommendationService — Recommandation déterministe du délai de relance.

Règles métier basées sur le type de source (proxy de la taille d'entreprise) :

  wttj / career_page  → startup          → 5 jours
  apec / api_officielle → grande entreprise → 10 jours
  indeed / linkedin   → entreprise moyenne → 7 jours
  défaut              → entreprise moyenne → 7 jours
"""
from datetime import datetime, timedelta, timezone


# source_type → (délai_jours, libellé)
_SOURCE_DELAY: dict[str, tuple[int, str]] = {
    "wttj": (5, "startup (WTTJ)"),
    "welcome_to_the_jungle": (5, "startup (WTTJ)"),
    "career_page": (5, "page carrière directe (startup présumée)"),
    "apec": (10, "grande entreprise (APEC)"),
    "api_officielle": (10, "grande entreprise (France Travail)"),
    "linkedin": (7, "entreprise moyenne (LinkedIn)"),
    "indeed": (7, "entreprise moyenne (Indeed)"),
}

_DEFAULT_DELAY = 7
_DEFAULT_REASON = "entreprise de taille inconnue"


class FollowupRecommendationService:
    """
    Retourne un dict compatible avec FollowupRecommendationOut.
    Aucune dépendance DB, aucun LLM.
    """

    def recommend(self, application) -> dict:
        """
        Calcule la recommandation de relance pour une candidature.

        Args:
            application: objet Application ORM (avec relation offer.primary_source chargée)

        Returns:
            dict: {recommended_delay_days, reason, suggested_date}
        """
        source_type = self._get_source_type(application)
        delay_days, reason = _SOURCE_DELAY.get(source_type or "", (_DEFAULT_DELAY, _DEFAULT_REASON))

        base = application.applied_at or application.created_at
        # Normaliser en UTC
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)

        suggested = base + timedelta(days=delay_days)

        return {
            "recommended_delay_days": delay_days,
            "reason": reason,
            "suggested_date": suggested,
        }

    @staticmethod
    def _get_source_type(application) -> str | None:
        try:
            return application.offer.primary_source.source_type if application.offer else None
        except AttributeError:
            return None
