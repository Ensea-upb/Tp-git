import logging
import time
from abc import ABC, abstractmethod

import httpx

from app.domain.dto.ingestion_report import IngestionReport
from app.domain.dto.raw_offer_payload import RawOfferPayload
from app.infrastructure.db.models.source import Source

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10.0   # secondes
_DEFAULT_RETRIES = 3
_RETRY_BACKOFF = [1.0, 2.0, 4.0]  # attentes entre tentatives


class BaseConnector(ABC):
    """
    Contrat commun pour tous les connecteurs de sources d'offres.

    Un connecteur est responsable uniquement de la collecte des données brutes.
    Il ne persiste rien en base et ne normalise rien.

    Méthodes publiques :
      - fetch()        : point d'entrée principal — wraps _do_fetch() avec retry,
                         timing et génération d'IngestionReport
      - is_available() : vérifie l'opérationnalité du connecteur
      - last_report    : rapport du dernier appel à fetch()

    Méthodes protégées pour les sous-classes :
      - _http_get(url, **kwargs)  : GET avec retry=3, timeout=10s
      - _http_post(url, **kwargs) : POST avec retry=3, timeout=10s
    """

    source_type: str = ""

    def __init__(self, source: Source) -> None:
        self.source = source
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._last_report: IngestionReport | None = None

    # ── Interface publique ─────────────────────────────────────────────

    def fetch(self) -> list[RawOfferPayload]:
        """
        Collecte les offres depuis la source.

        Wraps _do_fetch() avec :
        - mesure du temps d'exécution
        - comptage des erreurs
        - génération et log d'un IngestionReport
        """
        start = time.monotonic()
        errors = 0
        error_details: list[str] = []
        results: list[RawOfferPayload] = []

        try:
            results = self._do_fetch()
        except Exception as exc:
            errors += 1
            error_details.append(str(exc))
            self.logger.error(
                "%s fetch() a levé une exception non gérée : %s",
                self.__class__.__name__, exc,
            )

        duration = time.monotonic() - start
        report = IngestionReport(
            source=self.source.name,
            fetched=len(results),
            errors=errors,
            duration_seconds=round(duration, 3),
            error_details=error_details,
        )
        self._last_report = report
        self.logger.info("IngestionReport — %s", report)
        return results

    @property
    def last_report(self) -> IngestionReport | None:
        """Rapport du dernier appel à fetch(). None si fetch() n'a pas encore été appelé."""
        return self._last_report

    def is_available(self) -> bool:
        """Vérifie que le connecteur est opérationnel (credentials, connectivité)."""
        return True

    # ── Méthode abstraite ──────────────────────────────────────────────

    @abstractmethod
    def _do_fetch(self) -> list[RawOfferPayload]:
        """
        Implémentation de la collecte d'offres.

        Doit :
        - Retourner une liste de RawOfferPayload
        - Utiliser _http_get() / _http_post() pour les appels HTTP (retry + timeout)
        - Logger les erreurs partielles et continuer l'ingestion
        - Ne pas lever d'exception — en cas d'erreur fatale, retourner une liste vide
        """
        ...

    # ── Helpers HTTP avec retry ────────────────────────────────────────

    def _http_get(
        self,
        url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        retries: int = _DEFAULT_RETRIES,
        **kwargs,
    ) -> httpx.Response:
        """
        GET HTTP avec retry automatique.

        Lève la dernière exception si toutes les tentatives échouent.
        """
        return self._http_request("GET", url, timeout=timeout, retries=retries, **kwargs)

    def _http_post(
        self,
        url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        retries: int = _DEFAULT_RETRIES,
        **kwargs,
    ) -> httpx.Response:
        """
        POST HTTP avec retry automatique.

        Lève la dernière exception si toutes les tentatives échouent.
        """
        return self._http_request("POST", url, timeout=timeout, retries=retries, **kwargs)

    def _http_request(
        self,
        method: str,
        url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        retries: int = _DEFAULT_RETRIES,
        **kwargs,
    ) -> httpx.Response:
        last_exc: Exception = RuntimeError("Aucune tentative effectuée")
        for attempt in range(retries):
            try:
                resp = httpx.request(method, url, timeout=timeout, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as exc:
                last_exc = exc
                wait = _RETRY_BACKOFF[attempt] if attempt < len(_RETRY_BACKOFF) else 4.0
                self.logger.warning(
                    "%s %s tentative %d/%d échouée (%s) — retry dans %.1fs",
                    method, url, attempt + 1, retries, exc, wait,
                )
                if attempt < retries - 1:
                    time.sleep(wait)
        raise last_exc
