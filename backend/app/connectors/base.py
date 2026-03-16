import logging
from abc import ABC, abstractmethod

from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Contrat commun pour tous les connecteurs de sources d'offres.

    Un connecteur est responsable uniquement de la collecte des données brutes.
    Il ne persiste rien en base et ne normalise rien.
    """

    # Identifiant du type de source géré par ce connecteur (ex: "api_officielle")
    source_type: str = ""

    def __init__(self, source: Source) -> None:
        self.source = source
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def fetch(self) -> list[RawOfferPayload]:
        """
        Collecte les offres depuis la source configurée.
        Retourne une liste de RawOfferPayload.
        Ne lève pas d'exception — en cas d'erreur, log et retourne une liste vide.
        """
        ...

    def is_available(self) -> bool:
        """Vérifie que le connecteur est opérationnel (credentials, connectivité)."""
        return True
