"""
Registre des connecteurs.

Associe chaque source_type à sa classe de connecteur et instancie
le bon connecteur pour une source donnée.
"""

import logging

from app.connectors.base import BaseConnector
from app.connectors.france_travail import FranceTravailConnector
from app.connectors.http_career_page import HttpCareerPageConnector
from app.config import settings
from app.infrastructure.db.models.source import Source

logger = logging.getLogger(__name__)


class SourceConnectorManager:
    """
    Instancie le connecteur adapté pour une source donnée.
    Retourne None si le source_type est inconnu ou si le connecteur
    n'est pas disponible.
    """

    def get_connector(self, source: Source) -> BaseConnector | None:
        connector = self._build(source)
        if connector is None:
            logger.warning(
                "Aucun connecteur pour source_type='%s' (source='%s')",
                source.source_type,
                source.name,
            )
            return None

        if not connector.is_available():
            logger.info(
                "Connecteur non disponible pour '%s' — ignoré",
                source.name,
            )
            return None

        return connector

    def _build(self, source: Source) -> BaseConnector | None:
        match source.source_type:
            case "api_officielle":
                return FranceTravailConnector(
                    source=source,
                    client_id=settings.ft_client_id or "",
                    client_secret=settings.ft_client_secret or "",
                )
            case "career_page":
                return HttpCareerPageConnector(source=source)
            case _:
                return None
