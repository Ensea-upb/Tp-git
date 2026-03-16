"""
Connecteur LinkedIn — STUB (non implémenté, Sprint 7).

LinkedIn n'expose pas d'API publique pour la recherche d'offres depuis 2015.
L'accès programmatique nécessite :
  - LinkedIn Jobs API (partenaires certifiés uniquement)
  - OU scraping via Playwright/Selenium (interdit par CGU + requiert session auth)

Architecture préparée pour implémentation future :
  - source_type = "linkedin"
  - is_available() retourne False → connecteur ignoré par SourceConnectorManager
  - fetch() lève NotImplementedError pour signaler le manque d'implémentation

Pour implémenter :
  1. Obtenir accès LinkedIn Jobs API (programme partenaire)
     OU utiliser playwright-stealth après validation légale
  2. Implémenter _authenticate() avec OAuth2
  3. Implémenter fetch() avec pagination curseur LinkedIn
  4. Retourner RawOfferPayload(source_type="linkedin", ...)
"""

import logging

from app.connectors.base import BaseConnector
from app.domain.dto.raw_offer_payload import RawOfferPayload

logger = logging.getLogger(__name__)


class LinkedInConnector(BaseConnector):
    """
    Stub LinkedIn — retourne une liste vide et log un avertissement.
    Activer en Sprint 8+ une fois l'accès API ou la stratégie scraping validée.
    """

    source_type = "linkedin"

    def is_available(self) -> bool:
        # Toujours False jusqu'à implémentation complète
        logger.info(
            "LinkedInConnector non disponible — implémentation prévue Sprint 8+. "
            "Voir connectors/linkedin.py pour le roadmap."
        )
        return False

    def _do_fetch(self) -> list[RawOfferPayload]:
        raise NotImplementedError(
            "LinkedIn connector not yet implemented. "
            "is_available() returns False so this should never be called."
        )
